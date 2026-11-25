import json
import socket
import time
import sys
import dns.resolver

def comprobar_dns(nombre, dns_ip="127.0.0.1", dns_port=1053):
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [dns_ip]
    resolver.port = dns_port
    resolver.timeout = 5.0
    resolver.lifetime = 5.0

    inicio = time.time()
    try:
        respuesta = resolver.resolve(nombre, 'A')
        duracion = time.time() - inicio
        ip_resuelta = respuesta[0].to_text()
        
        if duracion > 1.0:
            return "lento", ip_resuelta, duracion, f"Respuesta lenta ({duracion:.2f}s)"
        return "correcto", ip_resuelta, duracion, "Resolución DNS OK"
    except dns.resolver.NXDOMAIN:
        duracion = time.time() - inicio
        return "fallo", None, duracion, f"El nombre {nombre} no existe en el DNS de pruebas."
    except dns.exception.Timeout:
        duracion = time.time() - inicio
        return "lento", None, duracion, f"Tiempo de espera DNS agotado ({duracion:.2f}s)"
    except Exception as e:
        duracion = time.time() - inicio
        return "fallo", None, duracion, f"Error en DNS: {str(e)}"

def comprobar_puerto(ip, puerto, timeout=3.0):
    inicio = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, puerto))
        duracion = time.time() - inicio
        s.close()
        return "correcto", duracion, "Puerto abierto OK"
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        duracion = time.time() - inicio
        s.close()
        return "fallo", duracion, f"Conexión rechazada o agotada en puerto {puerto}"

def main():
    try:
        with open("practicas/objetivos.json", "r", encoding="utf-8") as f:
            datos = json.load(f)
    except Exception as e:
        print(f"Error al cargar practicas/objetivos.json: {e}")
        sys.exit(1)

    print(f"{'DOMINIO':<26} | {'IP/ESTADO DNS':<16} | {'PUERTO':<7} | {'ESTADO TCP':<10} | {'TIEMPO':<8} | {'DETALLE'}")
    print("-" * 95)

    for srv in datos.get("servicios", []):
        nombre = srv["nombre"]
        puertos = srv.get("puertos", [])

        estado_dns, ip, t_dns, msg_dns = comprobar_dns(nombre)

        if estado_dns == "fallo" or not ip:
            print(f"{nombre:<26} | {'NO RESUELVE':<16} | {'-':<7} | {'FALLO':<10} | {t_dns*1000:>6.1f}ms | {msg_dns}")
            continue

        for p in puertos:
            estado_tcp, t_tcp, msg_tcp = comprobar_puerto(ip, p)
            estado_final = "correcto" if (estado_dns == "correcto" and estado_tcp == "correcto") else ("lento" if estado_dns == "lento" else "fallo")
            print(f"{nombre:<26} | {ip:<16} | {p:<7} | {estado_final.upper():<10} | {(t_dns+t_tcp)*1000:>6.1f}ms | {msg_dns if estado_dns != 'correcto' else msg_tcp}")

if __name__ == "__main__":
    main()
