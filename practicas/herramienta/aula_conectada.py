"""Punto de partida S4. Copia esta carpeta a tu espacio de equipo antes de editar.

Aquí empieza vuestro código. El laboratorio y su sonda interna son material de Educa360.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import socket
import ssl
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


def comprobar_puertos(requisitos, direcciones):
    inicio_total = time.perf_counter()
    dominios_req = requisitos.get("dominios", [])
    evidencias = []
    puertos_fallidos = []
    no_comprobados = []

    for item in dominios_req:
        if not isinstance(item, dict) or "nombre" not in item:
            continue
        dominio = item["nombre"]
        puertos = item.get("puertos", [])

        if dominio not in direcciones:
            lista_puertos = ", ".join(str(p.get("puerto")) for p in puertos if isinstance(p, dict) and "puerto" in p)
            no_comprobados.append(f"{dominio} (puertos {lista_puertos})")
            evidencias.append(
                f"{dominio} (puertos {lista_puertos}) -> no comprobado por falta de dirección resuelta en C-01"
            )
            continue

        ip = direcciones[dominio]
        for entrada_puerto in puertos:
            if not isinstance(entrada_puerto, dict) or "puerto" not in entrada_puerto:
                continue
            puerto = int(entrada_puerto["puerto"])
            protocolo = str(entrada_puerto.get("protocolo", "TCP")).upper()
            t0 = time.perf_counter()
            try:
                with socket.create_connection((ip, puerto), timeout=3.0):
                    ms = round((time.perf_counter() - t0) * 1000, 1)
                    evidencias.append(f"{dominio} ({ip}:{puerto}/{protocolo}) -> abierto (superada: {ms} ms)")
            except ConnectionRefusedError:
                ms = round((time.perf_counter() - t0) * 1000, 1)
                puertos_fallidos.append(f"{dominio} ({ip}:{puerto}/{protocolo}) rechazó la conexión")
                evidencias.append(
                    f"{dominio} ({ip}:{puerto}/{protocolo}) -> conexión rechazada / puerto cerrado (fallida: {ms} ms)"
                )
            except (TimeoutError, socket.timeout):
                ms = round((time.perf_counter() - t0) * 1000, 1)
                puertos_fallidos.append(f"{dominio} ({ip}:{puerto}/{protocolo}) agotó el tiempo límite de 3 s")
                evidencias.append(
                    f"{dominio} ({ip}:{puerto}/{protocolo}) -> tiempo agotado tras 3.0 s (fallida: {ms} ms)"
                )
            except OSError as exc:
                ms = round((time.perf_counter() - t0) * 1000, 1)
                puertos_fallidos.append(f"{dominio} ({ip}:{puerto}/{protocolo}) error de red ({exc})")
                evidencias.append(
                    f"{dominio} ({ip}:{puerto}/{protocolo}) -> error de conexión ({exc}) (fallida: {ms} ms)"
                )

    duracion_ms = round((time.perf_counter() - inicio_total) * 1000, 1)

    if puertos_fallidos:
        estado = "fallida"
        siguiente_paso = (
            "Revisa que el servicio esté escuchando y que el cortafuegos permita tráfico TCP en: "
            + "; ".join(puertos_fallidos) + "."
        )
    elif not evidencias or all("no comprobado" in e for e in evidencias):
        estado = "no_comprobada"
        siguiente_paso = "Resuelve primero C-01 (Resolución DNS) para obtener las direcciones IP antes de probar puertos."
    elif no_comprobados:
        estado = "superada"
        siguiente_paso = (
            "Los puertos con IP conocida están abiertos, pero quedaron sin comprobar por falta de resolución DNS en C-01: "
            + ", ".join(no_comprobados) + "."
        )
    else:
        estado = "superada"
        siguiente_paso = "Continuar con C-03 (HTTPS y certificado) sobre los puertos abiertos."

    return {
        "id": "C-02",
        "nombre": NOMBRES[1],
        "estado": estado,
        "evidencia": "; ".join(evidencias),
        "siguiente_paso": siguiente_paso,
        "duracion_ms": duracion_ms,
    }


def traducir_error_certificado(exc):
    codigo = getattr(exc, "verify_code", None)
    texto = f"{getattr(exc, 'verify_message', '')} {exc}".lower()

    if codigo == 10 or "expired" in texto:
        return (
            "caducado",
            "Renueva el certificado TLS del servidor y verifica que la fecha y hora del equipo sean correctas.",
        )
    if codigo == 62 or "hostname mismatch" in texto or "doesn't match" in texto or "ip address mismatch" in texto:
        return (
            "emitido para otro nombre",
            "Emite o instala un certificado TLS cuyo CN/SAN incluya exactamente el dominio solicitado.",
        )
    if codigo in (18, 19, 20, 21, 27) or "self-signed" in texto or "unable to get local issuer" in texto or "unable to verify the first certificate" in texto:
        return (
            "CA desconocida",
            "Comprueba que el servidor esté firmado por la CA esperada o indica la CA raíz correcta con --ca.",
        )
    detalle = getattr(exc, "verify_message", None) or str(exc)
    return (
        f"error de validación TLS ({detalle})",
        "Revisa la cadena de certificación y la configuración TLS del servicio.",
    )


def comprobar_https(requisitos, direcciones, ca_ruta):
    inicio_total = time.perf_counter()
    if not ca_ruta.is_file():
        raise ValueError(f"No se encuentra el fichero de CA '{ca_ruta}'. Indica una ruta válida con --ca.")

    try:
        contexto = ssl.create_default_context(cafile=str(ca_ruta))
        contexto.check_hostname = True
        contexto.verify_mode = ssl.CERT_REQUIRED
    except ssl.SSLError as exc:
        raise ValueError(f"El fichero de CA '{ca_ruta}' no es válido: {exc}") from None

    dominios_req = requisitos.get("dominios", [])
    evidencias = []
    fallos = []
    pasos_recomendados = []
    no_comprobados = []

    for item in dominios_req:
        if not isinstance(item, dict) or "nombre" not in item:
            continue
        dominio = item["nombre"]
        puertos = item.get("puertos", [])

        if dominio not in direcciones:
            lista_puertos = ", ".join(str(p.get("puerto")) for p in puertos if isinstance(p, dict) and "puerto" in p)
            no_comprobados.append(f"{dominio} (puertos {lista_puertos})")
            evidencias.append(
                f"https://{dominio} (puertos {lista_puertos}) -> no comprobado por falta de dirección resuelta en C-01"
            )
            continue

        ip = direcciones[dominio]
        for entrada_puerto in puertos:
            if not isinstance(entrada_puerto, dict) or "puerto" not in entrada_puerto:
                continue
            puerto = int(entrada_puerto["puerto"])
            t0 = time.perf_counter()
            try:
                with socket.create_connection((ip, puerto), timeout=5.0) as sock:
                    with contexto.wrap_socket(sock, server_hostname=dominio) as tls_sock:
                        peticion = (
                            f"GET /salud HTTP/1.1\r\n"
                            f"Host: {dominio}:{puerto}\r\n"
                            f"User-Agent: aula-conectada/0.4\r\n"
                            f"Connection: close\r\n\r\n"
                        ).encode("ascii")
                        tls_sock.sendall(peticion)
                        respuesta = b""
                        while b"\r\n" not in respuesta and len(respuesta) < 4096:
                            trozo = tls_sock.recv(1024)
                            if not trozo:
                                break
                            respuesta += trozo
                ms = round((time.perf_counter() - t0) * 1000, 1)
                primera_linea = respuesta.split(b"\r\n", 1)[0].decode("latin-1", errors="replace").strip()
                partes = primera_linea.split()
                codigo_http = int(partes[1]) if len(partes) >= 2 and partes[1].isdigit() else 0

                if codigo_http == 200:
                    evidencias.append(
                        f"https://{dominio}:{puerto}/salud ({ip}) -> HTTP 200 y certificado válido (superada: {ms} ms)"
                    )
                else:
                    detalle_http = primera_linea or "respuesta vacía"
                    fallos.append(f"https://{dominio}:{puerto}/salud devolvió '{detalle_http}'")
                    paso_http = f"Revisa el estado interno de https://{dominio}:{puerto}/salud (se esperaba HTTP 200)."
                    if paso_http not in pasos_recomendados:
                        pasos_recomendados.append(paso_http)
                    evidencias.append(
                        f"https://{dominio}:{puerto}/salud ({ip}) -> respuesta inesperada '{detalle_http}' (fallida: {ms} ms)"
                    )
            except ssl.SSLCertVerificationError as exc:
                ms = round((time.perf_counter() - t0) * 1000, 1)
                motivo, paso_cert = traducir_error_certificado(exc)
                fallos.append(f"{dominio}:{puerto} ({motivo})")
                if paso_cert not in pasos_recomendados:
                    pasos_recomendados.append(paso_cert)
                evidencias.append(
                    f"https://{dominio}:{puerto}/salud ({ip}) -> certificado inválido: {motivo} (fallida: {ms} ms)"
                )
            except ssl.SSLError as exc:
                ms = round((time.perf_counter() - t0) * 1000, 1)
                motivo, paso_cert = traducir_error_certificado(exc)
                fallos.append(f"{dominio}:{puerto} ({motivo})")
                if paso_cert not in pasos_recomendados:
                    pasos_recomendados.append(paso_cert)
                evidencias.append(
                    f"https://{dominio}:{puerto}/salud ({ip}) -> fallo TLS: {motivo} (fallida: {ms} ms)"
                )
            except (ConnectionRefusedError, TimeoutError, socket.timeout, OSError) as exc:
                ms = round((time.perf_counter() - t0) * 1000, 1)
                fallos.append(f"https://{dominio}:{puerto}/salud no responde ({exc})")
                paso_red = f"Verifica que el servicio HTTPS esté activo en {dominio}:{puerto}."
                if paso_red not in pasos_recomendados:
                    pasos_recomendados.append(paso_red)
                evidencias.append(
                    f"https://{dominio}:{puerto}/salud ({ip}) -> servicio HTTPS no accesible ({exc}) (fallida: {ms} ms)"
                )

    duracion_ms = round((time.perf_counter() - inicio_total) * 1000, 1)

    if fallos:
        estado = "fallida"
        siguiente_paso = " ".join(pasos_recomendados)
    elif not evidencias or all("no comprobado" in e for e in evidencias):
        estado = "no_comprobada"
        siguiente_paso = "Resuelve primero C-01 (Resolución DNS) antes de verificar HTTPS y certificados."
    elif no_comprobados:
        estado = "superada"
        siguiente_paso = (
            "Los servicios HTTPS con IP conocida responden 200 con certificado válido; sin comprobar por DNS: "
            + ", ".join(no_comprobados) + "."
        )
    else:
        estado = "superada"
        siguiente_paso = "Continuar con C-04 (Inspección TLS) para validar versión y cifrado."

    return {
        "id": "C-03",
        "nombre": NOMBRES[2],
        "estado": estado,
        "evidencia": f"CA {ca_ruta.name} | " + "; ".join(evidencias),
        "siguiente_paso": siguiente_paso,
        "duracion_ms": duracion_ms,
    }


def comprobar(requisitos, args):
    resultado_c01, direcciones = comprobar_dns(requisitos, args.dns)
    resultado_c02 = comprobar_puertos(requisitos, direcciones)
    resultado_c03 = comprobar_https(requisitos, direcciones, args.ca)
    resultados = [resultado_c01, resultado_c02, resultado_c03]
    for numero, nombre in enumerate(NOMBRES[3:], 4):
        # TU TAREA: implementar C-04 a C-08 con evidencia real y tiempo medido.
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
                 # Contrato ART-02 1.0 validado (normal, A-01 y rechazo enum)
                 "version_herramienta": "0.4-c03", "dns": args.dns, "proxy": args.proxy,
                 "requisitos": args.requisitos.name, "comprobaciones": comprobar(requisitos, args)}
    # TU TAREA: generar ART-03 (HTML) y ART-04 (texto y CSV), coherentes con este JSON.
    # TU TAREA: --ia añade una explicación opcional; sin clave o red, usa reglas.
    # Nunca envíes claves ni datos personales a la salida ni cambies los estados con IA.
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    c01 = resultado["comprobaciones"][0]
    c02 = resultado["comprobaciones"][1]
    c03 = resultado["comprobaciones"][2]
    print(f"Resultado guardado en {args.salida}. C-01: {c01['estado']} | C-02: {c02['estado']} | C-03: {c03['estado']} ({c03['duracion_ms']} ms).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(f"Parece que falta un paso: {exc}")
        sys.exit(1)

