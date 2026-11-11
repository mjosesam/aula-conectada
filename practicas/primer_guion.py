import argparse
from http.client import HTTPResponse
from pathlib import Path
import socket
import ssl
import dns.exception
import dns.resolver

def preguntar_dns(nombre, servidor="127.0.0.1", puerto=1053):
    consulta = dns.resolver.Resolver(configure=False)
    consulta.nameservers = [servidor]
    consulta.port = puerto
    consulta.timeout = 3
    consulta.lifetime = 5
    try:
        respuesta = consulta.resolve(nombre, "A", search=False)
        return respuesta[0].address
    except dns.resolver.NXDOMAIN:
        raise ValueError(f"El nombre {nombre} no existe en el DNS de pruebas.") from None
    except dns.exception.Timeout:
        raise ValueError("El DNS de pruebas no respondió a tiempo. Revisa su dirección y puerto.") from None
    except dns.exception.DNSException:
        raise ValueError("El DNS no pudo dar una dirección. Revisa la zona y si el laboratorio está en marcha.") from None

def pedir_salud(direccion, nombre, puerto, ca):
    try:
        contexto = ssl.create_default_context(cafile=str(ca))
        with socket.create_connection((direccion, puerto), timeout=5) as conexion:
            with contexto.wrap_socket(conexion, server_hostname=nombre) as canal:
                peticion = f"GET /salud HTTP/1.1\r\nHost: {nombre}:{puerto}\r\nConnection: close\r\n\r\n"
                canal.sendall(peticion.encode("ascii"))
                respuesta = HTTPResponse(canal)
                respuesta.begin()
                return respuesta.status, respuesta.read().decode("utf-8")
    except ssl.SSLCertVerificationError as error:
        motivos = {10: "el certificado ha caducado", 62: "el certificado es de otro nombre"}
        raise ValueError("Fallo HTTPS: " + motivos.get(error.verify_code, "la CA o la cadena del certificado no es fiable") + ".") from None
    except OSError:
        raise ValueError("No se pudo pedir /salud. Revisa la CA, la IP, el puerto y si el laboratorio está en marcha.") from None

def main():
    parser = argparse.ArgumentParser(description="Tu primer guion: dos nombres y una página de salud.")
    parser.add_argument("--dns", default="127.0.0.1:1053", help="Servidor y puerto del DNS de pruebas")
    parser.add_argument("--ca", required=True, type=Path, help="Desde equipo: ../lab/ca/ca-laboratorio.pem")
    args = parser.parse_args()
    servidor, puerto_texto = args.dns.rsplit(":", 1)
    puerto_dns = int(puerto_texto)

    ip_plataforma = None

    # 1. Comprobación DNS de plataforma.ejemplo.edu
    try:
        ip_plataforma = preguntar_dns("plataforma.ejemplo.edu", servidor, puerto_dns)
        print(f"plataforma.ejemplo.edu: correcto ({ip_plataforma})")
    except ValueError as e:
        print(f"plataforma.ejemplo.edu: fallo ({e})")

    # 2. Comprobación DNS de contenidos.ejemplo.edu
    try:
        ip_contenidos = preguntar_dns("contenidos.ejemplo.edu", servidor, puerto_dns)
        print(f"contenidos.ejemplo.edu: correcto ({ip_contenidos})")
    except ValueError as e:
        print(f"contenidos.ejemplo.edu: fallo ({e})")

    # 3. Comprobación HTTPS página de salud
    if ip_plataforma:
        try:
            estado, _ = pedir_salud(ip_plataforma, "plataforma.ejemplo.edu", 8443, args.ca)
            if estado == 200:
                print("salud plataforma: correcto (200 OK)")
            else:
                print(f"salud plataforma: fallo (código {estado})")
        except ValueError as e:
            print(f"salud plataforma: fallo ({e})")
    else:
        print("salud plataforma: fallo (No se puede probar HTTPS sin IP de plataforma)")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
