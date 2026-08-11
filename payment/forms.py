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
            'placeholder': 'e.g. 675123456 or 46733123454',
            'maxlength': '20',       # ✅ explicitly set HTML maxlength
            'minlength': '9',        # ✅ minimum 9 digits
            'inputmode': 'numeric',  # ✅ shows number keyboard on mobile
            'pattern': '[0-9]*',     # ✅ numbers only
        }),
        label='Phone Number',
        help_text='Cameroon number e.g. 675123456 | Sandbox test: 46733123454'
    )

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number'].strip().replace(' ', '').replace('-', '')

        # Strip country code if provided
        if phone.startswith('+237'):
            phone = phone[4:]
        if phone.startswith('237'):
            phone = phone[3:]

        # ✅ Allow MTN sandbox test numbers (46733123454 → after stripping 237 = 46733123454)
        SANDBOX_NUMBERS = ['46733123454', '46733123450', '46733123451']
        if phone in SANDBOX_NUMBERS:
            return phone

        # ✅ Allow real Cameroonian numbers: 9 digits starting with 6
        if not phone.startswith('6') or len(phone) != 9:
            raise forms.ValidationError(
                'Please enter a valid Cameroon mobile number (e.g. 670000000) '
                'or sandbox test number (46733123454).'
            )
        return phone