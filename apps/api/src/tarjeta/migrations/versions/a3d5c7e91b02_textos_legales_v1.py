"""Textos legales v1: términos del ciudadano, política de privacidad, convenio del comercio.

§13.2. Se cargan como textos legales versionados (tabla texto_legal), con la nota de
revisión legal visible en el propio texto. Fuente legible: docs/legal/*.md.

Revision ID: a3d5c7e91b02
Revises: e1f3b9c7a840
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "a3d5c7e91b02"
down_revision = "e1f3b9c7a840"
branch_labels = None
depends_on = None

_VERSION = "v1"

_TERMINOS_CIUDADANO = """# Términos y Condiciones — Tarjeta de Beneficios (ciudadanos)

> **Borrador redactado para revisión de Asesoría Letrada. No utilizar sin revisión legal.**

## 1. Qué es el programa

La Tarjeta de Beneficios es un programa del Municipio de Rivadavia (San Juan) que ofrece a las
vecinas y vecinos descuentos y beneficios en comercios adheridos. La participación es gratuita y
voluntaria.

## 2. Quién puede participar

Puede adherirse toda persona humana mayor de edad con documento nacional de identidad. La adhesión
se hace por la aplicación o de forma presencial, declarando los datos requeridos. La persona es
responsable de la veracidad de los datos que declara.

## 3. Niveles: Platino y Black

El programa tiene dos niveles. **Platino** es el nivel base de toda persona adherida. **Black** es
el nivel preferencial y se obtiene por estar al día con las obligaciones municipales según la
información del padrón municipal, o por herencia dentro de un grupo familiar (ver punto 5). El
nivel puede cambiar cuando cambia la situación en el padrón; el municipio no garantiza un nivel
permanente.

## 4. Puntos y vencimiento

Los canjes pueden otorgar puntos, según la mecánica de cada promoción. Los puntos **vencen a los
24 meses** de su acreditación. Los puntos no tienen valor monetario fuera del programa, no son
transferibles fuera de los mecanismos previstos y no se convierten en dinero.

## 5. Grupo familiar

El titular puede conformar un grupo familiar e invitar integrantes. Dentro del grupo puede
compartirse el nivel y, si el grupo así lo define, una billetera común de puntos. El titular es
responsable de las invitaciones y de la administración del grupo.

## 6. Responsabilidad del titular

La persona adherida es responsable de la información que declara y del uso de su tarjeta y sus
credenciales. El uso indebido, la declaración de datos falsos o el aprovechamiento fraudulento de
beneficios pueden dar lugar a la suspensión.

## 7. Causales de suspensión

El municipio puede suspender o dar de baja la participación ante: datos falsos, uso fraudulento,
abuso de los beneficios, o incumplimiento de estos términos. La suspensión se registra con su
motivo.

## 8. Modificaciones del programa

El municipio puede modificar el programa, sus beneficios y sus reglas, avisando por los canales
oficiales. El uso continuado de la tarjeta luego del aviso implica la aceptación de los cambios.

## 9. Datos personales

El tratamiento de datos personales se rige por la Política de Privacidad del programa y por la Ley
25.326 de Protección de Datos Personales.
"""

_PRIVACIDAD = """# Política de Privacidad — Tarjeta de Beneficios

> **Borrador redactado para revisión de Asesoría Letrada. No utilizar sin revisión legal.**

Esta política describe cómo el Municipio de Rivadavia (San Juan) trata los datos personales de las
personas adheridas a la Tarjeta de Beneficios. Marco legal: **Ley 25.326 de Protección de Datos
Personales**.

## 1. Qué datos se recogen

- Identificación: DNI y CUIL, nombre y apellido, fecha de nacimiento.
- Contacto: celular y, opcionalmente, correo electrónico.
- Datos de uso del programa: nivel, canjes, puntos, grupo familiar, dispositivos.
- Datos de ubicación **solo** si la persona lo consiente, para mostrar beneficios cercanos.

El DNI y el CUIL se almacenan **cifrados**. Nunca aparecen en registros de auditoría, en mensajes
de error ni en información visible para terceros.

## 2. Para qué se usan

Para operar el programa: determinar el nivel, aplicar descuentos, acreditar y controlar puntos,
administrar el grupo familiar y prevenir el fraude. No se venden ni se ceden a terceros con fines
comerciales.

## 3. Quién los ve

Solo el personal municipal autorizado, según su rol y con registro de auditoría. **El comercio
adherido nunca accede a los datos de contacto, de domicilio ni fiscales de la persona.** En una
operación, el comercio ve únicamente lo mínimo para aplicar el beneficio (por ejemplo, nombre e
inicial del apellido y el nivel), nunca el DNI, el CUIL ni el teléfono.

## 4. Cuánto tiempo se guardan

Mientras dure la participación en el programa y por el plazo que exijan las obligaciones legales y
de auditoría. Los registros contables y de auditoría son inmutables por diseño.

## 5. Derechos de la persona (Ley 25.326)

Toda persona puede ejercer los derechos de **acceso, rectificación y supresión** de sus datos, y
oponerse a tratamientos no obligatorios (como las comunicaciones comerciales o la geolocalización).
Para ejercerlos, dirigirse a los canales oficiales del municipio. La autoridad de control en la
materia es la Agencia de Acceso a la Información Pública.

## 6. Consentimientos

Al adherirse, la persona presta el consentimiento obligatorio para el tratamiento de datos
necesario para operar el programa, y puede otorgar o revocar por separado los consentimientos
opcionales (comunicaciones comerciales, geolocalización, estadística anónima).
"""

_CONVENIO_COMERCIO = """# Convenio de Adhesión del Comercio — Tarjeta de Beneficios

> **Borrador redactado para revisión de Asesoría Letrada. No utilizar sin revisión legal.**

Este convenio regula la adhesión de un comercio a la Tarjeta de Beneficios del Municipio de
Rivadavia (San Juan). Al adherirse, el comercio acepta estas condiciones. Es el instrumento que
obliga al comercio mientras no exista una ordenanza específica.

## 1. Descuento a cargo del comercio

El comercio **absorbe en su totalidad** el descuento que ofrece a través del programa. El municipio
no reintegra ni subsidia el descuento, salvo que un acuerdo específico y por escrito diga lo
contrario.

## 2. El comercio fija el porcentaje

El comercio **fija libremente** el porcentaje o la mecánica de sus promociones, dentro de las
opciones que ofrece el programa, y puede darlas de alta o de baja según su conveniencia comercial.

## 3. Respetar lo publicado

El comercio se compromete a **respetar en el mostrador** exactamente lo que publica en la
aplicación: el mismo descuento, en las mismas condiciones y durante la vigencia informada.

## 4. No aumentar precios para compensar

El comercio **no puede aumentar los precios** de los bienes o servicios alcanzados para compensar el
descuento del programa. El beneficio debe ser real para la persona.

## 5. Suspensión y baja por el municipio

El municipio puede **suspender o dar de baja** al comercio, con **motivo registrado**, ante
incumplimientos de este convenio (por ejemplo, no respetar lo publicado, aumentar precios para
compensar, o conducta que perjudique a las personas del programa).

## 6. Uso de imagen y logo

El comercio autoriza el uso de su **nombre, imagen y logo** en la aplicación y en los canales
oficiales del municipio, con el fin de difundir su participación y sus promociones. Puede revocar
esta autorización al darse de baja.

## 7. Vigencia y baja voluntaria

La adhesión rige desde su aprobación y por tiempo indeterminado. El comercio puede solicitar la
**baja voluntaria** en cualquier momento por los canales oficiales; la baja no afecta las
operaciones ya realizadas ni las obligaciones pendientes.

## 8. Datos

El comercio trata los datos de las operaciones conforme a la normativa vigente y a la Política de
Privacidad del programa, y no accede a datos de contacto, domicilio ni fiscales de las personas.
"""

_TEXTOS: dict[str, str] = {
    "TERMINOS_CIUDADANO": _TERMINOS_CIUDADANO,
    "PRIVACIDAD": _PRIVACIDAD,
    "CONVENIO_COMERCIO": _CONVENIO_COMERCIO,
}


def upgrade() -> None:
    conn = op.get_bind()
    stmt = sa.text(
        "INSERT INTO texto_legal (id, tipo, version, texto, vigente) "
        "VALUES (:id, :tipo, :version, :texto, true)"
    )
    for tipo, texto in _TEXTOS.items():
        conn.execute(
            stmt,
            {"id": str(uuid.uuid4()), "tipo": tipo, "version": _VERSION, "texto": texto},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM texto_legal WHERE version = :v AND tipo = ANY(:tipos)"),
        {"v": _VERSION, "tipos": list(_TEXTOS.keys())},
    )
