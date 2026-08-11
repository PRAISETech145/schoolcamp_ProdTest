import uuid
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.urls import reverse
from datetime import timedelta

from .models import Subscription, Payment, SUBSCRIPTION_AMOUNT
from .forms import PaymentForm
from .momo import mtn_request_to_pay, orange_request_to_pay

logger = logging.getLogger(__name__)


def get_or_create_subscription(user):
    sub, created = Subscription.objects.get_or_create(user=user)
    return sub


def subscription_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        sub = get_or_create_subscription(request.user)
        if not sub.is_active:
            messages.warning(request, '⏰ Your free trial has expired. Please subscribe to continue.')
            return redirect('payment:wall')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@login_required
def payment_wall(request):
    sub = get_or_create_subscription(request.user)
    form = PaymentForm()
    return render(request, 'payment/wall.html', {'sub': sub, 'form': form, 'amount': SUBSCRIPTION_AMOUNT})


@login_required
def initiate_payment(request):
    if request.method != 'POST':
        return redirect('payment:wall')

    form = PaymentForm(request.POST)
    if not form.is_valid():
        sub = get_or_create_subscription(request.user)
        return render(request, 'payment/wall.html', {'sub': sub, 'form': form, 'amount': SUBSCRIPTION_AMOUNT})

    provider = form.cleaned_data['provider']
    phone = form.cleaned_data['phone_number']
    reference = f"SC-{uuid.uuid4().hex[:10].upper()}"

    payment = Payment.objects.create(
        user=request.user,
        provider=provider,
        phone_number=phone,
        amount=SUBSCRIPTION_AMOUNT,
        reference=reference,
        status='pending',
    )

    webhook_url = request.build_absolute_uri(reverse('payment:webhook'))

    try:
        if provider == 'mtn':
            mtn_request_to_pay(
                amount=SUBSCRIPTION_AMOUNT,
                phone=phone,
                reference=reference,
                callback_url=webhook_url,
            )
            return redirect('payment:pending', pk=payment.pk)

        elif provider == 'orange':
            result = orange_request_to_pay(
                amount=SUBSCRIPTION_AMOUNT,
                phone=phone,
                reference=reference,
                callback_url=webhook_url,
            )
            if isinstance(result, str) and result.startswith('http'):
                return redirect(result)
            return redirect('payment:pending', pk=payment.pk)

    except Exception as e:
        logger.error(f"Payment API error [{provider}] for {request.user}: {e}")
        payment.status = 'failed'
        payment.save()
        messages.error(
            request,
            f'Could not reach {provider.upper()} payment service. '
            'Please check your number and try again.'
        )
        return redirect('payment:wall')


@login_required
def payment_pending(request, pk):
    payment = get_object_or_404(Payment, pk=pk, user=request.user)
    return render(request, 'payment/pending.html', {'payment': payment})


@login_required
def payment_status(request, pk):
    payment = get_object_or_404(Payment, pk=pk, user=request.user)
    return JsonResponse({'status': payment.status})


@login_required
def confirm_payment(request, pk):
    """DEV ONLY — simulates successful payment. Remove in production."""
    payment = get_object_or_404(Payment, pk=pk, user=request.user)
    if payment.status == 'pending':
        payment.status = 'completed'
        payment.confirmed_at = timezone.now()
        payment.save()
        sub = get_or_create_subscription(request.user)
        sub.status = 'active'
        sub.paid_until = timezone.now() + timedelta(days=30)
        sub.save()
        messages.success(request, '🎉 Payment confirmed! Welcome to SchoolCamp Premium.')
    return redirect('payment:success')


@login_required
def payment_success(request):
    sub = get_or_create_subscription(request.user)
    return render(request, 'payment/success.html', {'sub': sub})


@login_required
def payment_failed(request, pk):
    payment = get_object_or_404(Payment, pk=pk, user=request.user)
    if payment.status == 'pending':
        payment.status = 'failed'
        payment.save()
    return render(request, 'payment/failed.html', {'payment': payment})


@login_required
def subscription_status(request):
    sub = get_or_create_subscription(request.user)
    return render(request, 'payment/status.html', {'sub': sub})


# ── Webhook ──────────────────────────────────────────────────────────────────
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def payment_webhook(request):
    """Receives async callbacks from MTN MoMo and Orange Money."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        logger.info(f"Webhook received: {data}")

        reference = data.get('externalId') or data.get('order_id') or data.get('reference')
        raw_status = data.get('status', '').upper()
        operator_ref = data.get('financialTransactionId') or data.get('txnid', '')

        payment = Payment.objects.get(reference=reference)

        if raw_status in ('SUCCESSFUL', 'SUCCESS', 'COMPLETED'):
            payment.status = 'completed'
            payment.operator_reference = operator_ref
            payment.confirmed_at = timezone.now()
            payment.save()
            sub = get_or_create_subscription(payment.user)
            sub.status = 'active'
            sub.paid_until = timezone.now() + timedelta(days=30)
            sub.save()
            logger.info(f"Payment {reference} completed for {payment.user}")

        elif raw_status in ('FAILED', 'REJECTED', 'TIMEOUT', 'CANCELLED'):
            payment.status = 'failed'
            payment.save()
            logger.warning(f"Payment {reference} failed: {raw_status}")

        return JsonResponse({'received': True})

    except Payment.DoesNotExist:
        return JsonResponse({'error': 'Payment not found'}, status=404)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JsonResponse({'error': str(e)}, status=400)