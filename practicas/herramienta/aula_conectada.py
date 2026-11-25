"""Punto de partida S4. Copia esta carpeta a tu espacio de equipo antes de editar.

Aquí empieza vuestro código. El laboratorio y su sonda interna son material de Educa360.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys

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


def comprobar(requisitos, args):
    resultados = []
    for numero, nombre in enumerate(NOMBRES, 1):
        # TU TAREA: implementar C-01 a C-08 con evidencia real y tiempo medido.
        # Usa args.dns, args.proxy y args.ca sin modificar la configuración del equipo.
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
                 "version_herramienta": "0.1-inicio", "dns": args.dns, "proxy": args.proxy,
                 "requisitos": args.requisitos.name, "comprobaciones": comprobar(requisitos, args)}
    # TU TAREA: generar ART-03 (HTML) y ART-04 (texto y CSV), coherentes con este JSON.
    # TU TAREA: --ia añade una explicación opcional; sin clave o red, usa reglas.
    # Nunca envíes claves ni datos personales a la salida ni cambies los estados con IA.
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Resultado guardado en {args.salida}. Las comprobaciones siguen pendientes de implementar.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(f"Parece que falta un paso: {exc}")
        sys.exit(1)
