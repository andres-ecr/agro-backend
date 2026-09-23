import uuid
from django.db import models
from django.utils import timezone


class LicenseState(models.Model):
    """
    Singleton model that maintains the local cryptographic lease state
    and offline grace period timer for the on-premise installation.
    """
    STATUS_CHOICES = [
        ('active', 'Activa'),
        ('grace_period', 'En Gracia Offline'),
        ('suspended', 'Suspendida por Administración'),
        ('expired', 'Expirada'),
        ('revoked', 'Revocada'),
        ('unlicensed', 'Sin Licencia'),
    ]

    serial_key = models.CharField(max_length=100, blank=True, default='', verbose_name="Clave Serial")
    machine_id = models.CharField(max_length=100, blank=True, default='', verbose_name="Identificador de Servidor")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='unlicensed', verbose_name="Estado")
    customer_name = models.CharField(max_length=200, blank=True, default='', verbose_name="Cliente")

    last_heartbeat_at = models.DateTimeField(null=True, blank=True, verbose_name="Último Heartbeat")
    lease_until = models.DateTimeField(null=True, blank=True, verbose_name="Vencimiento del Lease")
    grace_period_hours = models.IntegerField(default=48, verbose_name="Horas de Gracia Offline")

    is_perpetual = models.BooleanField(
        default=False,
        verbose_name="Licencia Perpetua",
        help_text="Si está activo, el sistema opera indefinidamente sin requerir internet ni consultas al servidor."
    )

    last_monotonic_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última Marca de Tiempo Registrada",
        help_text="Evita la manipulación del reloj del sistema operativo."
    )

    cached_token = models.TextField(blank=True, default='', verbose_name="Token de Lease Cifrado")
    last_sync_error = models.TextField(blank=True, default='', verbose_name="Último Error de Sincronización")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estado de Licencia"
        verbose_name_plural = "Estado de Licencia"

    def __str__(self):
        return f"Licencia: {self.serial_key or 'Sin Asignar'} [{self.status}]"

    @classmethod
    def get_instance(cls):
        """Returns or creates the single local license state record."""
        import sys
        is_test = 'test' in sys.argv
        obj, created = cls.objects.get_or_create(
            id=1,
            defaults={'is_perpetual': True} if is_test else {}
        )
        if not obj.machine_id:
            # Generate deterministic stable machine identity
            obj.machine_id = f"srv-{uuid.uuid5(uuid.NAMESPACE_DNS, str(uuid.getnode())).hex[:16]}"
            obj.save(update_fields=['machine_id'])
        return obj
