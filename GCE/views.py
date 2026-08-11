import uuid
import os
import mimetypes
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from .models import Material, MaterialPurchase, DownloadToken, Subject, Solutions, SolutionPurchase
from .forms import PaymentForm


# ── Public listing ────────────────────────────────────────────

def material_list(request):
    """Main materials page — shows all available PDFs."""
    subjects     = Subject.objects.all()
    subject_slug = request.GET.get('subject', '')
    level        = request.GET.get('level', '')
    query        = request.GET.get('q', '')

    materials = Material.objects.filter(is_active=True).select_related('subject')

    if subject_slug:
        materials = materials.filter(subject__slug=subject_slug)
    if level:
        materials = materials.filter(level=level)
    if query:
        materials = materials.filter(title__icontains=query)

    purchased_ids = set()
    if request.user.is_authenticated:
        purchased_ids = set(
            MaterialPurchase.objects.filter(
                user=request.user, is_valid=True
            ).values_list('material_id', flat=True)
        )

    return render(request, 'GCE/list.html', {
        'materials':        materials,
        'subjects':         subjects,
        'purchased_ids':    purchased_ids,
        'selected_subject': subject_slug,
        'selected_level':   level,
        'query':            query,
    })


def material_detail(request, pk):
    """Detail page for a single material — includes solution if one exists."""
    material = get_object_or_404(Material, pk=pk, is_active=True)

    # Load the approved solution for this material (None if not available)
    solution = Solutions.objects.filter(paper=material, is_approved=True).first()

    has_access      = material.user_has_access(request.user)
    solution_access = solution.user_has_access(request.user) if solution else False

    form = PaymentForm()
    return render(request, 'GCE/detail.html', {
        'material':        material,
        'has_access':      has_access,
        'solution':        solution,
        'solution_access': solution_access,
        'form':            form,
    })


# ── Material payment ──────────────────────────────────────────

@login_required
def initiate_purchase(request, pk):
    """Handle payment form submission for a material."""
    material = get_object_or_404(Material, pk=pk, is_active=True)

    if material.user_has_access(request.user):
        messages.info(request, '✅ You already have access to this material.')
        return redirect('GCE:download_ready', pk=pk)

    if request.method != 'POST':
        return redirect('GCE:detail', pk=pk)

    form = PaymentForm(request.POST)
    if not form.is_valid():
        return render(request, 'GCE/detail.html', {
            'material':   material,
            'has_access': False,
            'form':       form,
        })

    provider  = form.cleaned_data['provider']
    phone     = form.cleaned_data['phone_number']
    reference = f"MAT-{uuid.uuid4().hex[:10].upper()}"

    purchase, created = MaterialPurchase.objects.get_or_create(
        user=request.user,
        material=material,
        defaults={
            'amount_paid':  material.price,
            'provider':     provider,
            'phone_number': phone,
            'reference':    reference,
            'status':       'pending',
        }
    )

    if not created:
        purchase.provider     = provider
        purchase.phone_number = phone
        purchase.reference    = reference
        purchase.status       = 'pending'
        purchase.is_valid     = False
        purchase.save()

    from payment.momo import mtn_request_to_pay, orange_request_to_pay
    from django.urls import reverse

    webhook_url = request.build_absolute_uri(reverse('GCE:webhook'))

    try:
        if provider == 'mtn':
            mtn_request_to_pay(amount=material.price, phone=phone,
                               reference=reference, callback_url=webhook_url)
        elif provider == 'orange':
            orange_request_to_pay(amount=material.price, phone=phone,
                                  reference=reference, callback_url=webhook_url)
    except Exception:
        purchase.status = 'failed'
        purchase.save()
        messages.error(request, f'Could not reach {provider.upper()} service. Please try again.')
        return redirect('GCE:detail', pk=pk)

    return redirect('GCE:purchase_pending', pk=purchase.pk)


@login_required
def purchase_pending(request, pk):
    """Waiting screen while user approves on phone."""
    purchase = get_object_or_404(MaterialPurchase, pk=pk, user=request.user)
    return render(request, 'GCE/pending.html', {'purchase': purchase})


@login_required
def purchase_status(request, pk):
    """AJAX poll — returns current purchase status."""
    purchase = get_object_or_404(MaterialPurchase, pk=pk, user=request.user)
    return JsonResponse({'status': purchase.status})


@login_required
def download_ready(request, pk):
    """Page shown after successful payment — with download button."""
    material = get_object_or_404(Material, pk=pk, is_active=True)
    if not material.user_has_access(request.user):
        messages.warning(request, '⚠️ Please complete payment to access this material.')
        return redirect('GCE:detail', pk=pk)

    purchase = MaterialPurchase.objects.filter(
        user=request.user, material=material, is_valid=True
    ).first()

    token = DownloadToken.objects.create(purchase=purchase)

    return render(request, 'GCE/download_ready.html', {
        'material': material,
        'token':    token,
    })


# ── Secure file download ──────────────────────────────────────

def secure_download(request, token):
    """Serve the PDF file using a one-time token. Never exposes the real file path."""
    download_token = get_object_or_404(DownloadToken, token=token)

    if not download_token.is_valid:
        raise Http404('This download link has expired or already been used.')

    download_token.used = True
    download_token.save()

    material = download_token.purchase.material

    file_path = material.file.path
    if not os.path.exists(file_path):
        raise Http404('File not found.')

    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or 'application/octet-stream'

    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{material.title}.pdf"'
    return response


# ── Solution purchase ─────────────────────────────────────────

@login_required
def initiate_solution_purchase(request, solution_pk):
    """Handle 50 XAF payment form submission for a solution."""
    solution = get_object_or_404(Solutions, pk=solution_pk, is_approved=True)

    if solution.user_has_access(request.user):
        messages.info(request, '✅ You already have access to this solution.')
        return redirect('GCE:solution_download_ready', solution_pk=solution_pk)

    if request.method != 'POST':
        return redirect('GCE:detail', pk=solution.paper.pk)

    provider  = request.POST.get('provider', '').strip()
    phone     = request.POST.get('phone_number', '').strip()

    if not provider or not phone:
        messages.error(request, 'Please select an operator and enter your phone number.')
        return redirect('GCE:detail', pk=solution.paper.pk)

    reference = f"SOL-{uuid.uuid4().hex[:10].upper()}"

    purchase, created = SolutionPurchase.objects.get_or_create(
        user=request.user,
        solution=solution,
        defaults={
            'amount_paid':  solution.price,
            'provider':     provider,
            'phone_number': phone,
            'reference':    reference,
            'status':       'pending',
        }
    )

    if not created:
        # Reset a previous failed attempt
        purchase.provider     = provider
        purchase.phone_number = phone
        purchase.reference    = reference
        purchase.status       = 'pending'
        purchase.is_valid     = False
        purchase.save()

    from payment.momo import mtn_request_to_pay, orange_request_to_pay
    from django.urls import reverse

    webhook_url = request.build_absolute_uri(reverse('GCE:solution_webhook'))

    try:
        if provider == 'mtn':
            mtn_request_to_pay(amount=solution.price, phone=phone,
                               reference=reference, callback_url=webhook_url)
        elif provider == 'orange':
            orange_request_to_pay(amount=solution.price, phone=phone,
                                  reference=reference, callback_url=webhook_url)
    except Exception:
        purchase.status = 'failed'
        purchase.save()
        messages.error(request, f'Could not reach {provider.upper()} service. Please try again.')
        return redirect('GCE:detail', pk=solution.paper.pk)

    return redirect('GCE:solution_purchase_pending', pk=purchase.pk)


@login_required
def solution_purchase_pending(request, pk):
    """Waiting screen while user approves solution payment on phone."""
    purchase = get_object_or_404(SolutionPurchase, pk=pk, user=request.user)
    return render(request, 'GCE/solution_pending.html', {'purchase': purchase})


@login_required
def solution_purchase_status(request, pk):
    """AJAX poll — returns current solution purchase status."""
    purchase = get_object_or_404(SolutionPurchase, pk=pk, user=request.user)
    return JsonResponse({'status': purchase.status})


@login_required
def solution_download_ready(request, solution_pk):
    """Serve the solution file after verifying purchase."""
    solution = get_object_or_404(Solutions, pk=solution_pk, is_approved=True)

    if not solution.user_has_access(request.user):
        messages.warning(request, '⚠️ Please complete payment to access this solution.')
        return redirect('GCE:detail', pk=solution.paper.pk)

    file_path = solution.solution.path
    if not os.path.exists(file_path):
        raise Http404('Solution file not found.')

    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or 'application/octet-stream'

    # Increment download count
    Solutions.objects.filter(pk=solution.pk).update(
        download_count=solution.download_count + 1
    )

    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{solution.title}.pdf"'
    return response


# ── Solution webhook ──────────────────────────────────────────

@csrf_exempt
def solution_payment_webhook(request):
    """Receives callbacks from MTN MoMo / Orange Money for solution purchases."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data       = json.loads(request.body)
        reference  = data.get('externalId') or data.get('order_id') or data.get('reference')
        raw_status = data.get('status', '').upper()

        purchase = SolutionPurchase.objects.get(reference=reference)

        if raw_status in ('SUCCESSFUL', 'SUCCESS', 'COMPLETED'):
            purchase.confirm()
        elif raw_status in ('FAILED', 'REJECTED', 'TIMEOUT', 'CANCELLED'):
            purchase.status = 'failed'
            purchase.save()

        return JsonResponse({'received': True})
    except SolutionPurchase.DoesNotExist:
        return JsonResponse({'error': 'Purchase not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ── Material webhook ──────────────────────────────────────────

@csrf_exempt
def payment_webhook(request):
    """Receives callbacks from MTN MoMo / Orange Money for material purchases."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data       = json.loads(request.body)
        reference  = data.get('externalId') or data.get('order_id') or data.get('reference')
        raw_status = data.get('status', '').upper()

        purchase = MaterialPurchase.objects.get(reference=reference)

        if raw_status in ('SUCCESSFUL', 'SUCCESS', 'COMPLETED'):
            purchase.confirm()
        elif raw_status in ('FAILED', 'REJECTED', 'TIMEOUT', 'CANCELLED'):
            purchase.status = 'failed'
            purchase.save()

        return JsonResponse({'received': True})
    except MaterialPurchase.DoesNotExist:
        return JsonResponse({'error': 'Purchase not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ── Dev helpers ───────────────────────────────────────────────

@login_required
def confirm_purchase_dev(request, pk):
    """DEV ONLY — simulate successful material payment. Remove in production."""
    purchase = get_object_or_404(MaterialPurchase, pk=pk, user=request.user)
    if purchase.status == 'pending':
        purchase.confirm()
        messages.success(request, '✅ Payment confirmed! Your material is ready.')
    return redirect('GCE:download_ready', pk=purchase.material.pk)


@login_required
def confirm_solution_purchase_dev(request, pk):
    """DEV ONLY — simulate successful solution payment. Remove in production."""
    purchase = get_object_or_404(SolutionPurchase, pk=pk, user=request.user)
    if purchase.status == 'pending':
        purchase.confirm()
        messages.success(request, '✅ Payment confirmed! Your solution is ready.')
    return redirect('GCE:solution_download_ready', solution_pk=purchase.solution.pk)
