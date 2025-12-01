from django import forms
from django.contrib import admin

from iot.models import IoTDataSource, IoTDataToken
from iot.utils import clear_source_names_from_cache


class IoTDataTokenAdmin(admin.ModelAdmin):
    pass


class IoTdataSourceForm(forms.ModelForm):
    class Meta:
        model = IoTDataSource
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        token_headers = cleaned_data.get("token_headers", None)
        if token_headers is not None and not any(
            "<token>" in val for val in token_headers.values()
        ):
            raise forms.ValidationError(
                "The 'token_headers' must contain '<token>' in a value field."
            )

        headers = cleaned_data.get("headers", None)
        if headers and token_headers:
            raise forms.ValidationError(
                "The 'headers' and 'token_headers' fields are mutually exclusive."
            )

        return cleaned_data


class IoTDataSourceAdmin(admin.ModelAdmin):
    list_display = ("source_full_name",)

    form = IoTdataSourceForm

    def save_model(self, request, obj, form, change):
        # clear the cache of source_names
        clear_source_names_from_cache()
        return super().save_model(request, obj, form, change)


admin.site.register(IoTDataToken, IoTDataTokenAdmin)
admin.site.register(IoTDataSource, IoTDataSourceAdmin)
