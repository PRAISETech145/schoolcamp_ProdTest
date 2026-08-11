import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
from django.db.models import Q
from .models import Material, MaterialPurchase
from .forms import MaterialUploadForm
from payment.views import subscription_required


@login_required
@subscription_required
def materials_list_view(request):
    materials = Material.objects.filter(is_approved=True).select_related('uploader')
    subject = request.GET.get('subject', '')
    level = request.GET.get('level', '')
    search = request.GET.get('q', '')
    

    if subject:
        materials = materials.filter(subject=subject)
    if level:
        materials = materials.filter(level=level)
    if search:
        materials = materials.filter(Q(title__icontains=search) | Q(description__icontains=search))
   

    from .models import SUBJECT_CHOICES, LEVEL_CHOICES
    context = {
        'materials': materials,
        'subject_choices': SUBJECT_CHOICES,
        'level_choices': LEVEL_CHOICES,
        'active_subject': subject,
        'active_level': level,
        'search': search,
        
    }
    return render(request, 'materials/list.html', context)

@login_required
@subscription_required
def material_detail_view(request, pk):
    material = get_object_or_404(Material, pk=pk, is_approved=True)
    has_access = False
    if request.user.is_authenticated:
            has_access = True
    elif request.user == material.uploader or request.user.is_staff:
        has_access = True
    else:
        has_access = MaterialPurchase.objects.filter(
            user=request.user, material=material
        ).exists()

    context = {
        'material': material,
        'has_access': has_access,
    }
    return render(request, 'materials/detail.html', context)


@login_required
@subscription_required
def download_material_view(request, pk):
    material = get_object_or_404(Material, pk=pk, is_approved=True)
    has_access = False
    
    has_access = True
    if request.user == material.uploader or request.user.is_staff:
        has_access = True
    else:
        has_access = MaterialPurchase.objects.filter(
            user=request.user, material=material
        ).exists()

    if not has_access:
        messages.error(request, 'You need to purchase this material to download it.')
        return redirect('payments:initiate', material_pk=pk)
 
    try:
        file_path = material.file.path
        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=os.path.basename(file_path)
        )
        material.download_count += 1
        material.save(update_fields=['download_count'])
        return response
    except FileNotFoundError:
        raise Http404("File not found.")


@login_required
@subscription_required
def upload_material_view(request):
    if request.method == 'POST':
        form = MaterialUploadForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.uploader = request.user
            material.save()
            request.user.add_xp(20)
            messages.success(request, f'"{material.title}" uploaded successfully! 🎉')
            return redirect('materials:detail', pk=material.pk)
    else:
        form = MaterialUploadForm()
    return render(request, 'materials/upload.html', {'form': form})


@login_required
def my_materials_view(request): 
    uploaded = Material.objects.filter(uploader=request.user).order_by('-created_at')
    purchased = MaterialPurchase.objects.filter(user=request.user).select_related('material').order_by('-purchased_at')
    context = {'uploaded': uploaded, 'purchased': purchased}
    return render(request, 'materials/my_materials.html', context)


@login_required
def delete_material_view(request, pk):
    material = get_object_or_404(Material, pk=pk, uploader=request.user)
    if request.method == 'POST':
        material.file.delete(save=False)
        material.delete()
        messages.success(request, 'Material deleted.')
        return redirect('materials:my_materials')
    return render(request, 'materials/confirm_delete.html', {'material': material})

def Maths_view(request):
    return render(request,'materials/math_library.html')

def physics_view(request):
    return render(request,'materials/physics_library.html')

def chemistry_view(request):
    return render(request,'materials/chemistry_library.html')

def Biology_view(request):
    return render(request,'materials/biology_library.html')

def computerScience_view(request):
    return render(request,'materials/csc_library.html')

def french_view(request):
    return render(request,'materials/french.html')

def Economics_view(request):
    return render(request,'materials/economics_library.html')
