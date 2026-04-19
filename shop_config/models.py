from django.db import models

class ShopConfiguration(models.Model):
    shop_name = models.CharField(max_length=255, default="Bluebell Interiors")
    upi_id = models.CharField(max_length=255, blank=True, null=True)

    def build_upi_url(self, amount=None, note=None, currency="INR", fallback_upi_id="shopowner@upi"):
        from decimal import Decimal, ROUND_HALF_UP
        from urllib.parse import urlencode, quote

        pa = (self.upi_id or "").strip() or fallback_upi_id
        pn = (self.shop_name or "").strip() or "Bluebell Interiors"

        params = {
            "pa": pa,
            "pn": pn,
        }

        if amount is not None:
            if isinstance(amount, Decimal):
                amount_value = str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            else:
                amount_value = str(amount)
            params["am"] = amount_value
            params["cu"] = currency

        if note:
            params["tn"] = str(note)

        return "upi://pay?" + urlencode(params, quote_via=quote, safe="")
    
    def __str__(self):
        return self.shop_name

    class Meta:
        verbose_name = "Shop Configuration"
        verbose_name_plural = "Shop Configuration"
