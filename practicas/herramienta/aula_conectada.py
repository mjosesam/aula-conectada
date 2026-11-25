"""Punto de partida S4. Copia esta carpeta a tu espacio de equipo antes de editar.

Aquí empieza vuestro código. El laboratorio y su sonda interna son material de Educa360.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time

import dns.exception
import dns.resolver

NOMBRES = ["Resolución DNS", "Conexión a puertos", "HTTPS y certificado", "Inspección TLS",
           "Canal en tiempo real", "Descarga", "Latencia y estabilidad", "Proxy del sistema"]


def cargar_requisitos(ruta):
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise ValueError(
            f"No se encuentra el fichero de requisitos '{ruta}'. "
            "Comprueba que el archivo existe o indica una ruta válida con --requisitos."
        ) from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Revisa {ruta.name}, línea {exc.lineno}: el JSON no se puede leer.") from None
    if not isinstance(datos, dict):
        raise ValueError("Revisa la raíz del fichero: se espera un objeto JSON.")
    # TU TAREA (R-01): validar campos y tipos de ART-01; señalar campo y línea.
    # Poder leer un JSON no significa que sus requisitos sean válidos.
    return datos


def parsear_dns(dns_arg):
    if ":" in dns_arg:
        host, puerto_txt = dns_arg.rsplit(":", 1)
        try:
            puerto = int(puerto_txt)
        except ValueError:
            raise ValueError(f"Puerto DNS no válido en '{dns_arg}'. Usa formato IP:puerto.") from None
    else:
        host, puerto = dns_arg, 53
    if not host or not (1 <= puerto <= 65535):
        raise ValueError(f"Dirección DNS no válida en '{dns_arg}'. Usa formato IP:puerto.")
    return host, puerto


def comprobar_dns(requisitos, dns_arg):
    inicio_total = time.perf_counter()
    host_dns, puerto_dns = parsear_dns(dns_arg)

    resolvedor = dns.resolver.Resolver(configure=False)
    resolvedor.nameservers = [host_dns]
    resolvedor.port = puerto_dns
    resolvedor.timeout = 5.0
    resolvedor.lifetime = 5.0

    dominios = [item["nombre"] for item in requisitos.get("dominios", []) if isinstance(item, dict) and "nombre" in item]
    if not dominios:
        raise ValueError("El fichero de requisitos no contiene dominios válidos en 'dominios'.")

    direcciones = {}
    evidencias = []
    hay_fallo = False
    hay_duda = False

    for dominio in dominios:
        t0 = time.perf_counter()
        try:
            respuesta = resolvedor.resolve(dominio, "A", lifetime=5.0)
            ms = round((time.perf_counter() - t0) * 1000, 1)
            ip = respuesta[0].to_text()
            direcciones[dominio] = ip
            if ms >= 1000.0:
                hay_duda = True
                evidencias.append(f"{dominio} -> {ip} (dudosa: {ms} ms)")
            else:
                evidencias.append(f"{dominio} -> {ip} (superada: {ms} ms)")
        except dns.resolver.NXDOMAIN:
            ms = round((time.perf_counter() - t0) * 1000, 1)
            hay_fallo = True
            evidencias.append(f"{dominio} -> sin respuesta NXDOMAIN (fallida: {ms} ms)")
        except dns.resolver.NoAnswer:
            ms = round((time.perf_counter() - t0) * 1000, 1)
            hay_fallo = True
            evidencias.append(f"{dominio} -> sin registro A (fallida: {ms} ms)")
        except (dns.resolver.LifetimeTimeout, dns.resolver.NoNameservers, dns.exception.DNSException, OSError):
            ms = round((time.perf_counter() - t0) * 1000, 1)
            hay_fallo = True
            evidencias.append(f"{dominio} -> el DNS {host_dns}:{puerto_dns} no responde (fallida: {ms} ms)")

    duracion_ms = round((time.perf_counter() - inicio_total) * 1000, 1)

    if hay_fallo:
        estado = "fallida"
        siguiente_paso = (
            f"Verifica que el servidor DNS {host_dns}:{puerto_dns} esté activo y tenga registros A para todos los dominios."
        )
    elif hay_duda:
        estado = "dudosa"
        siguiente_paso = (
            f"Revisa la latencia del servidor DNS {host_dns}:{puerto_dns}: uno o más dominios superan 1000 ms."
        )
    else:
        estado = "superada"
        siguiente_paso = "Continuar con C-02 (Conexión a puertos) usando las direcciones resueltas."

    resultado_c01 = {
        "id": "C-01",
        "nombre": NOMBRES[0],
        "estado": estado,
        "evidencia": f"DNS {host_dns}:{puerto_dns} | " + "; ".join(evidencias),
        "siguiente_paso": siguiente_paso,
        "duracion_ms": duracion_ms,
    }
    return resultado_c01, direcciones


def comprobar(requisitos, args):
    resultado_c01, direcciones = comprobar_dns(requisitos, args.dns)
    resultados = [resultado_c01]
    for numero, nombre in enumerate(NOMBRES[1:], 2):
        # TU TAREA: implementar C-02 a C-08 con evidencia real y tiempo medido.
        # Usa direcciones (de C-01), args.proxy y args.ca sin modificar la configuración del equipo.
        # Mantén el nombre TLS al conectar a la dirección obtenida del DNS de pruebas.
        # Si una comprobación anterior te impide continuar, explica por qué.
        resultados.append({"id": f"C-{numero:02}", "nombre": nombre, "estado": "no_comprobada",
                           "evidencia": "Pendiente de implementar por el equipo.",
                           "siguiente_paso": "Construir y probar esta comprobación.", "duracion_ms": 0})
    return resultados


def main():
    parser = argparse.ArgumentParser(description="Herramienta de vuestro equipo de Aula conectada.")
    parser.add_argument("--requisitos", type=Path, required=True)
    parser.add_argument("--dns", default="127.0.0.1:1053")
    parser.add_argument("--proxy", default=None)
    parser.add_argument("--ca", type=Path, required=True)
    parser.add_argument("--salida", type=Path, default=Path("salidas/resultado.json"), help="Ruta desde tu terminal; por defecto salidas/resultado.json")
    parser.add_argument("--ia", action="store_true")
    args = parser.parse_args()
    requisitos = cargar_requisitos(args.requisitos)
    resultado = {"fecha": datetime.now(timezone.utc).isoformat(), "sistema_operativo": platform.system(),
                 "version_herramienta": "0.2-c01", "dns": args.dns, "proxy": args.proxy,
                 "requisitos": args.requisitos.name, "comprobaciones": comprobar(requisitos, args)}
    # TU TAREA: generar ART-03 (HTML) y ART-04 (texto y CSV), coherentes con este JSON.
    # TU TAREA: --ia añade una explicación opcional; sin clave o red, usa reglas.
    # Nunca envíes claves ni datos personales a la salida ni cambies los estados con IA.
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    c01 = resultado["comprobaciones"][0]
    print(f"Resultado guardado en {args.salida}. C-01 ({c01['nombre']}): {c01['estado']} ({c01['duracion_ms']} ms).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(f"Parece que falta un paso: {exc}")
        sys.exit(1)
