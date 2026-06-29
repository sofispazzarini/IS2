from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from user.models import User, Profesor
from actividad.models import Actividad
from turno.models import Salon, Clase, Reserva, TurnoFijo, Abono, ListaEspera
from pago.models import Pago
from core.models import ConfiguracionSistema


class Command(BaseCommand):
    help = 'Crea datos de prueba para demo del sistema'

    def handle(self, *args, **options):
        self.stdout.write('=' * 60)
        self.stdout.write('CREANDO DATOS DE PRUEBA PARA DEMO')
        self.stdout.write('=' * 60 + '\n')

        # Configuración del sistema
        ConfiguracionSistema.obtener()

        # ═══════════════════════════════════════════════════════════
        # 👤 USUARIOS
        # ═══════════════════════════════════════════════════════════
        self.stdout.write('\n👤 USUARIOS')
        self.stdout.write('-' * 40)

        # Cliente abonado (demo en vivo) - con pack activo y créditos
        cliente_abonado, created = User.objects.get_or_create(
            email='cliente@demo.com',
            defaults={
                'username': 'cliente@demo.com',
                'first_name': 'María',
                'last_name': 'Demo',
                'dni': '33000001',
                'telefono': '1155550001',
                'rol': 'cliente',
                'creditos': Decimal('15000'),
            }
        )
        if created:
            cliente_abonado.set_password('demo1234')
            cliente_abonado.save()
        self.stdout.write(f'  ✓ Cliente abonado: cliente@demo.com (tiene créditos: ${cliente_abonado.creditos})')

        # Cliente para lista de espera
        cliente_espera, created = User.objects.get_or_create(
            email='espera@demo.com',
            defaults={
                'username': 'espera@demo.com',
                'first_name': 'Juan',
                'last_name': 'Espera',
                'dni': '33000002',
                'telefono': '1155550002',
                'rol': 'cliente',
                'creditos': Decimal('0'),
            }
        )
        if created:
            cliente_espera.set_password('demo1234')
            cliente_espera.save()
        self.stdout.write(f'  ✓ Cliente para lista espera: espera@demo.com')

        # Clientes para llenar cupo de Clase B
        clientes_relleno = []
        for i in range(1, 6):
            cliente, created = User.objects.get_or_create(
                email=f'relleno{i}@demo.com',
                defaults={
                    'username': f'relleno{i}@demo.com',
                    'first_name': f'Relleno{i}',
                    'last_name': 'Usuario',
                    'dni': f'3300010{i}',
                    'telefono': f'115555010{i}',
                    'rol': 'cliente',
                }
            )
            if created:
                cliente.set_password('demo1234')
                cliente.save()
            clientes_relleno.append(cliente)
        self.stdout.write(f'  ✓ 5 clientes para llenar cupo de Clase B')

        # Secretario
        secretario, created = User.objects.get_or_create(
            email='secretario@demo.com',
            defaults={
                'username': 'secretario@demo.com',
                'first_name': 'Ana',
                'last_name': 'Secretaria',
                'dni': '22000001',
                'telefono': '1155551001',
                'rol': 'secretario',
            }
        )
        if created:
            secretario.set_password('demo1234')
            secretario.save()
        self.stdout.write(f'  ✓ Secretario: secretario@demo.com')

        # Dueño
        dueno, created = User.objects.get_or_create(
            email='dueno@demo.com',
            defaults={
                'username': 'dueno@demo.com',
                'first_name': 'Carlos',
                'last_name': 'Dueño',
                'dni': '11000001',
                'telefono': '1155552001',
                'rol': 'dueno',
            }
        )
        if created:
            dueno.set_password('demo1234')
            dueno.save()
        self.stdout.write(f'  ✓ Dueño: dueno@demo.com')

        # ═══════════════════════════════════════════════════════════
        # 🏃 ACTIVIDADES
        # ═══════════════════════════════════════════════════════════
        self.stdout.write('\n🏃 ACTIVIDADES')
        self.stdout.write('-' * 40)

        zona_media, _ = Actividad.objects.get_or_create(
            nombre='ZONA MEDIA',
            defaults={
                'descripcion': 'Entrenamiento enfocado en la zona media: abdominales, oblicuos y espalda baja.',
                'duracion_min': 60,
                'precio': Decimal('5000'),
            }
        )
        self.stdout.write(f'  ✓ Actividad 1: ZONA MEDIA (${zona_media.precio})')

        zona_inferior, _ = Actividad.objects.get_or_create(
            nombre='ZONA INFERIOR',
            defaults={
                'descripcion': 'Entrenamiento de piernas, glúteos y pantorrillas.',
                'duracion_min': 60,
                'precio': Decimal('5000'),
            }
        )
        self.stdout.write(f'  ✓ Actividad 2: ZONA INFERIOR (${zona_inferior.precio})')

        zona_superior, _ = Actividad.objects.get_or_create(
            nombre='ZONA SUPERIOR',
            defaults={
                'descripcion': 'Entrenamiento de hombros, pecho, espalda y brazos.',
                'duracion_min': 60,
                'precio': Decimal('5000'),
            }
        )
        self.stdout.write(f'  ✓ Actividad 3: ZONA SUPERIOR (${zona_superior.precio})')

        # ═══════════════════════════════════════════════════════════
        # 🧑‍🏫 PROFESORES
        # ═══════════════════════════════════════════════════════════
        self.stdout.write('\n🧑‍🏫 PROFESORES')
        self.stdout.write('-' * 40)

        profesor_zona_media, _ = Profesor.objects.get_or_create(
            dni=40000001,
            defaults={
                'nombre': 'Laura',
                'apellido': 'García',
                'telefono': '1155553001',
                'email': 'laura.garcia@gym.com',
                'especialidad': 'Zona Media',
            }
        )
        self.stdout.write(f'  ✓ Profesor 1: {profesor_zona_media} (Zona Media)')

        profesor_zona_inferior, _ = Profesor.objects.get_or_create(
            dni=40000002,
            defaults={
                'nombre': 'Martín',
                'apellido': 'Pérez',
                'telefono': '1155553002',
                'email': 'martin.perez@gym.com',
                'especialidad': 'Zona Inferior',
            }
        )
        self.stdout.write(f'  ✓ Profesor 2: {profesor_zona_inferior} (Zona Inferior)')

        profesor_zona_superior, _ = Profesor.objects.get_or_create(
            dni=40000003,
            defaults={
                'nombre': 'Carolina',
                'apellido': 'López',
                'telefono': '1155553003',
                'email': 'carolina.lopez@gym.com',
                'especialidad': 'Zona Superior',
            }
        )
        self.stdout.write(f'  ✓ Profesor 3: {profesor_zona_superior} (Zona Superior)')

        # ═══════════════════════════════════════════════════════════
        # 🏠 SALONES
        # ═══════════════════════════════════════════════════════════
        salon_a, _ = Salon.objects.get_or_create(nombre='Salón A')
        salon_b, _ = Salon.objects.get_or_create(nombre='Salón B')

        # ═══════════════════════════════════════════════════════════
        # 📅 CLASES
        # ═══════════════════════════════════════════════════════════
        self.stdout.write('\n📅 CLASES')
        self.stdout.write('-' * 40)

        hoy = date.today()
        manana = hoy + timedelta(days=1)
        pasado = hoy + timedelta(days=2)
        en_3_dias = hoy + timedelta(days=3)
        en_4_dias = hoy + timedelta(days=4)
        en_5_dias = hoy + timedelta(days=5)
        en_6_dias = hoy + timedelta(days=6)
        en_7_dias = hoy + timedelta(days=7)

        # Clase A - CON CUPO DISPONIBLE, para demo en vivo (pedir turno → confirmar → pagar)
        clase_a = self._crear_clase_si_no_existe(
            actividad=zona_media,
            profesor=profesor_zona_media,
            fecha=manana,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            cupo_maximo=15,
            salon=salon_a,
            nombre='Clase A'
        )
        self.stdout.write(f'  ✓ Clase A: {zona_media.nombre} - {manana} 10:00hs (cupo: 15, DISPONIBLE para demo)')

        # Clase B - CUPO LLENO, para mostrar lista de espera
        clase_b = self._crear_clase_si_no_existe(
            actividad=zona_inferior,
            profesor=profesor_zona_inferior,
            fecha=manana,
            hora_inicio=time(18, 0),
            hora_fin=time(19, 0),
            cupo_maximo=5,
            salon=salon_b,
            nombre='Clase B'
        )
        self.stdout.write(f'  ✓ Clase B: {zona_inferior.nombre} - {manana} 18:00hs (cupo: 5, se llenará)')

        # Clase C - FECHA DISTINTA, para filtros
        clase_c = self._crear_clase_si_no_existe(
            actividad=zona_media,
            profesor=profesor_zona_media,
            fecha=pasado,
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            cupo_maximo=15,
            salon=salon_a,
            nombre='Clase C'
        )
        self.stdout.write(f'  ✓ Clase C: {zona_media.nombre} - {pasado} 09:00hs (para filtros por fecha)')

        # Clase D - CON INSCRIPTO LISTO PARA REGISTRAR ASISTENCIA
        clase_d = self._crear_clase_si_no_existe(
            actividad=zona_superior,
            profesor=profesor_zona_superior,
            fecha=en_3_dias,
            hora_inicio=time(17, 0),
            hora_fin=time(18, 0),
            cupo_maximo=10,
            salon=salon_b,
            nombre='Clase D'
        )
        self.stdout.write(f'  ✓ Clase D: {zona_superior.nombre} - {en_3_dias} 17:00hs (para registrar asistencia)')

        # Clases E-J: Más clases próximas para probar
        clase_e = self._crear_clase_si_no_existe(
            actividad=zona_media,
            profesor=profesor_zona_media,
            fecha=en_4_dias,
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            cupo_maximo=12,
            salon=salon_a,
            nombre='Clase E'
        )
        self.stdout.write(f'  ✓ Clase E: {zona_media.nombre} - {en_4_dias} 09:00hs')

        clase_f = self._crear_clase_si_no_existe(
            actividad=zona_inferior,
            profesor=profesor_zona_inferior,
            fecha=en_4_dias,
            hora_inicio=time(18, 0),
            hora_fin=time(19, 0),
            cupo_maximo=10,
            salon=salon_b,
            nombre='Clase F'
        )
        self.stdout.write(f'  ✓ Clase F: {zona_inferior.nombre} - {en_4_dias} 18:00hs')

        clase_g = self._crear_clase_si_no_existe(
            actividad=zona_superior,
            profesor=profesor_zona_superior,
            fecha=en_5_dias,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            cupo_maximo=15,
            salon=salon_a,
            nombre='Clase G'
        )
        self.stdout.write(f'  ✓ Clase G: {zona_superior.nombre} - {en_5_dias} 10:00hs')

        clase_h = self._crear_clase_si_no_existe(
            actividad=zona_media,
            profesor=profesor_zona_media,
            fecha=en_5_dias,
            hora_inicio=time(17, 0),
            hora_fin=time(18, 0),
            cupo_maximo=8,
            salon=salon_b,
            nombre='Clase H'
        )
        self.stdout.write(f'  ✓ Clase H: {zona_media.nombre} - {en_5_dias} 17:00hs')

        clase_i = self._crear_clase_si_no_existe(
            actividad=zona_inferior,
            profesor=profesor_zona_inferior,
            fecha=en_6_dias,
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            cupo_maximo=12,
            salon=salon_a,
            nombre='Clase I'
        )
        self.stdout.write(f'  ✓ Clase I: {zona_inferior.nombre} - {en_6_dias} 09:00hs')

        clase_j = self._crear_clase_si_no_existe(
            actividad=zona_superior,
            profesor=profesor_zona_superior,
            fecha=en_7_dias,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            cupo_maximo=10,
            salon=salon_b,
            nombre='Clase J'
        )
        self.stdout.write(f'  ✓ Clase J: {zona_superior.nombre} - {en_7_dias} 10:00hs')

        # ═══════════════════════════════════════════════════════════
        # 🎟️ TURNOS Y RESERVAS
        # ═══════════════════════════════════════════════════════════
        self.stdout.write('\n🎟️ TURNOS Y RESERVAS')
        self.stdout.write('-' * 40)

        # Turno confirmado del cliente abonado (para cancelar en demo)
        if clase_c:
            reserva_cancelable, created = Reserva.objects.get_or_create(
                usuario=cliente_abonado,
                clase=clase_c,
                defaults={
                    'estado': 'confirmada',
                    'monto_pagado': zona_media.precio,
                }
            )
            if created:
                Pago.objects.create(
                    reserva=reserva_cancelable,
                    monto=zona_media.precio,
                    metodo_pago='creditos',
                    estado_pago='aprobado',
                    registrado_por=dueno,
                )
            self.stdout.write(f'  ✓ Turno CONFIRMADO de cliente@demo.com en Clase C (listo para cancelar)')

        # Llenar Clase B con reservas para que quede LLENA
        if clase_b:
            for i, cliente in enumerate(clientes_relleno):
                reserva, created = Reserva.objects.get_or_create(
                    usuario=cliente,
                    clase=clase_b,
                    defaults={
                        'estado': 'confirmada',
                        'monto_pagado': zona_inferior.precio,
                    }
                )
                if created:
                    Pago.objects.create(
                        reserva=reserva,
                        monto=zona_inferior.precio,
                        metodo_pago='efectivo',
                        estado_pago='aprobado',
                        registrado_por=secretario,
                    )
            self.stdout.write(f'  ✓ Clase B llenada con 5 reservas (cupo completo)')

            # Usuario en lista de espera de Clase B
            lista_espera, _ = ListaEspera.objects.get_or_create(
                usuario=cliente_espera,
                clase=clase_b,
            )
            self.stdout.write(f'  ✓ espera@demo.com en LISTA DE ESPERA de Clase B')

        # Reserva en Clase D lista para registrar asistencia
        if clase_d:
            reserva_asistencia, created = Reserva.objects.get_or_create(
                usuario=cliente_abonado,
                clase=clase_d,
                defaults={
                    'estado': 'confirmada',
                    'monto_pagado': zona_superior.precio,
                }
            )
            if created:
                Pago.objects.create(
                    reserva=reserva_asistencia,
                    monto=zona_superior.precio,
                    metodo_pago='mercado_pago',
                    estado_pago='aprobado',
                )
            self.stdout.write(f'  ✓ cliente@demo.com en Clase D (listo para registrar asistencia)')
            #self.stdout.write(f'    QR UUID: {reserva_asistencia.qr_uuid}')

        # ═══════════════════════════════════════════════════════════
        # 💰 PAGOS HISTÓRICOS (para estadísticas)
        # ═══════════════════════════════════════════════════════════
        self.stdout.write('\n💰 PAGOS HISTÓRICOS (para estadísticas)')
        self.stdout.write('-' * 40)

        # Crear pagos adicionales con distintos métodos usando las reservas existentes de Clase B
        # Los pagos ya existen en efectivo, agregamos más con otros métodos
        reservas_clase_b = Reserva.objects.filter(clase=clase_b)
        metodos_adicionales = ['posnet', 'tarjeta', 'mercado_pago']

        for i, reserva in enumerate(reservas_clase_b[:3]):
            metodo = metodos_adicionales[i]
            # Verificar si ya existe un pago con este método para esta reserva
            if not Pago.objects.filter(reserva=reserva, metodo_pago=metodo).exists():
                Pago.objects.create(
                    reserva=reserva,
                    monto=Decimal('5000'),
                    metodo_pago=metodo,
                    estado_pago='aprobado',
                    registrado_por=secretario,
                )

        # Agregar más pagos con distintos métodos a otras clases
        if clase_a:
            for i, metodo in enumerate(['efectivo', 'posnet', 'tarjeta', 'mercado_pago']):
                cliente = clientes_relleno[i % len(clientes_relleno)]
                reserva, created = Reserva.objects.get_or_create(
                    usuario=cliente,
                    clase=clase_a,
                    defaults={
                        'estado': 'confirmada',
                        'monto_pagado': Decimal('5000'),
                    }
                )
                if created:
                    Pago.objects.create(
                        reserva=reserva,
                        monto=Decimal('5000'),
                        metodo_pago=metodo,
                        estado_pago='aprobado',
                        registrado_por=secretario,
                    )

        self.stdout.write(f'  ✓ Pagos con distintos métodos agregados')
        self.stdout.write(f'    Métodos: efectivo, posnet, tarjeta, mercado_pago')

        # ═══════════════════════════════════════════════════════════
        # 📦 TURNO FIJO Y ABONO (para cliente abonado)
        # ═══════════════════════════════════════════════════════════
        self.stdout.write('\n📦 TURNO FIJO Y ABONO')
        self.stdout.write('-' * 40)

        turno_fijo, _ = TurnoFijo.objects.get_or_create(
            usuario=cliente_abonado,
            dia_semana=0,  # Lunes
            hora_inicio=time(10, 0),
            defaults={
                'actividad': zona_media,
                'activo': True,
            }
        )
        self.stdout.write(f'  ✓ Turno fijo: cliente@demo.com - Lunes 10:00hs (ZONA MEDIA)')

        abono, _ = Abono.objects.get_or_create(
            usuario=cliente_abonado,
            mes=hoy.month,
            anio=hoy.year,
            defaults={
                'cantidad_turnos_fijos': 4,
                'descuento_porcentaje': 10,
                'monto_total': zona_media.precio * 4,
                'monto_final': zona_media.precio * 4 * Decimal('0.9'),
                'metodo_pago': 'transferencia',
                'estado_pago': 'aprobado',
            }
        )
        self.stdout.write(f'  ✓ Abono {hoy.month}/{hoy.year} aprobado para cliente@demo.com')

        # ═══════════════════════════════════════════════════════════
        # RESUMEN FINAL
        # ═══════════════════════════════════════════════════════════
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('✅ SEED COMPLETADO')
        self.stdout.write('=' * 60)

        self.stdout.write('\n📋 CREDENCIALES (password: demo1234)')
        self.stdout.write('-' * 40)
        self.stdout.write(f'  👤 Cliente abonado:  cliente@demo.com')
        self.stdout.write(f'  👤 Cliente espera:   espera@demo.com')
        self.stdout.write(f'  👔 Secretario:       secretario@demo.com')
        self.stdout.write(f'  👑 Dueño:            dueno@demo.com')

        self.stdout.write('\n📌 PARA LA DEMO')
        self.stdout.write('-' * 40)
        self.stdout.write(f'  • Clase A ({manana}): cupo disponible → pedir turno')
        self.stdout.write(f'  • Clase B ({manana}): cupo LLENO → lista de espera (mensaje amarillo)')
        self.stdout.write(f'  • Clase C ({pasado}): turno cancelable')
        self.stdout.write(f'  • Clase D ({en_3_dias}): registrar asistencia')
        self.stdout.write(f'  • Clases E-J: más clases próximas para probar')

        self.stdout.write('\n📊 ESTADÍSTICAS')
        self.stdout.write('-' * 40)
        self.stdout.write(f'  • Efectivo: $15000')
        self.stdout.write(f'  • Posnet: $10000')
        self.stdout.write(f'  • Tarjeta: $10000')
        self.stdout.write(f'  • MercadoPago: $15000')
        self.stdout.write('')

    def _crear_clase_si_no_existe(self, actividad, profesor, fecha, hora_inicio, hora_fin, cupo_maximo, salon, nombre):
        existe = Clase.objects.filter(
            fecha=fecha,
            hora_inicio=hora_inicio,
            salon=salon
        ).first()

        if existe:
            return existe

        clase = Clase(
            actividad=actividad,
            profesor=profesor,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            cupo_maximo=cupo_maximo,
            salon=salon,
        )
        clase.save()
        return clase
