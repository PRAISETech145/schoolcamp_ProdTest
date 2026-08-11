from django import forms


class PaymentForm(forms.Form):
    PROVIDER_CHOICES = [
        ('mtn', 'MTN Mobile Money'),
        ('orange', 'Orange Money'),
    ]

    provider = forms.ChoiceField(
        choices=PROVIDER_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'provider-radio'})
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. 6XXXXXXXX',
        }),
        label='Phone Number',
        help_text='Enter the mobile money number to be charged'
    )

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number'].strip().replace(' ', '').replace('-', '')
        # Accept Cameroon format: 6XXXXXXXX (9 digits) or +237XXXXXXXXX
        if phone.startswith('+237'):
            phone = phone[4:]
        if phone.startswith('237'):
            phone = phone[3:]
        if not phone.startswith('6') or len(phone) != 9:
            raise forms.ValidationError(
                'Please enter a valid Cameroon mobile number (e.g. 670000000)'
            )
        return phone