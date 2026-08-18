import os
import re
import json
from datetime import datetime
import pandas as pd


# ==========================
# CONFIG
# ==========================
EXCEL_DIR = r"D:\ANALISIS DE DATOS\BASE DE DATOS 2026"  # <-- tu carpeta de excels
OUT_DIR = os.path.join(os.path.dirname(__file__), "data")
LIMIT_FILES = 0  # 0 = sin límite, >0 limita cantidad de excels (para pruebas)

os.makedirs(OUT_DIR, exist_ok=True)

# ==========================
# HELPERS
# ==========================
def norm_col(s: str) -> str:
    """Normaliza nombres de columnas para buscarlas sin fallar por puntos/espacios."""
    s = str(s).strip().lower()
    s = s.replace("\n", " ")
    s = re.sub(r"\s+", " ", s)
    # normaliza variaciones comunes
    s = s.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u").replace("ñ","n")
    return s

def canon_dni(v) -> str:
    """DNI solo dígitos (evita 12345678.0, espacios, etc.)."""
    s = "" if v is None else str(v).strip()
    return re.sub(r"\D", "", s)

def pick_value(row: dict, candidates: list[str], default=""):
    for c in candidates:
        if c in row:
            v = row.get(c)
            if v is None:
                continue
            vs = str(v).strip()
            if vs != "" and vs.lower() != "nan":
                return v
    return default

def parse_date_any(v):
    """Intenta sacar fecha de varios formatos."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None

    # Prueba formatos comunes
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt)
        except:
            pass

    # Si viene como "2025-12-10 00:00:00"
    try:
        return pd.to_datetime(s, errors="coerce").to_pydatetime()
    except:
        return None

def detect_columns(df: pd.DataFrame):
    """Devuelve mapeo normalizado: col_norm -> col_original"""
    mp = {}
    for c in df.columns:
        mp[norm_col(c)] = c
    return mp

def read_excel_any(path: str) -> pd.DataFrame:
    """Lee el excel (primera hoja) de forma robusta."""
    try:
        return pd.read_excel(path, engine="openpyxl")
    except Exception:
        # fallback: intenta sin engine
        return pd.read_excel(path)

# ==========================
# MAIN
# ==========================
def main():
    files = [f for f in os.listdir(EXCEL_DIR) if f.lower().endswith((".xlsx", ".xls"))]
    files.sort()

    if LIMIT_FILES > 0:
        files = files[:LIMIT_FILES]

    if not files:
        print("❌ No encontré excels en:", EXCEL_DIR)
        return

    # Agrupar registros por (anio, mes)
    buckets: dict[tuple[int,int], list[dict]] = {}

    total_rows = 0
    used_rows = 0

    for i, fn in enumerate(files, 1):
        path = os.path.join(EXCEL_DIR, fn)
        print(f"📄 [{i}/{len(files)}] Leyendo: {fn}")

        try:
            df = read_excel_any(path)
        except Exception as e:
            print("   ⚠️ No pude leer:", fn, "->", e)
            continue

        if df is None or df.empty:
            print("   ⚠️ Vacío:", fn)
            continue

        colmap = detect_columns(df)

        # Mapeos: intentamos encontrar columnas por nombre
        # Fecha
        fecha_col = None
        for cand in [
            "fecha atencion", "fecha de atencion", "fec atencion", "fec. atencion",
            "fecha", "fecha_atencion"
        ]:
            if cand in colmap:
                fecha_col = colmap[cand]
                break

        # Establecimiento
        eess_col = None
        for cand in [
            "eess", "establecimiento", "ipress", "nombre eess", "establecimieto", "establecimiento de salud"
        ]:
            if cand in colmap:
                eess_col = colmap[cand]
                break

        # Profesional (nombre)
        prof_col = None
        for cand in [
            "profesional", "nombres profesional", "nombre profesional", "profesional responsable",
            "responsable atencion", "resp. aten.", "resp aten", "personal"
        ]:
            if cand in colmap:
                prof_col = colmap[cand]
                break

        # Tipo profesional
        tipo_col = None
        for cand in [
            "tipo profesional", "tipo_profesional", "profesion", "profesión", "tipo personal", "cargo"
        ]:
            if cand in colmap:
                tipo_col = colmap[cand]
                break

        # DNI PROFESIONAL (clave): DNI Resp. Aten.
        dni_prof_col = None
        for cand in [
            "dni resp. aten.", "dni resp aten", "dni responsable", "dni_responsable",
            "dni profesional", "dni del profesional", "dni_profesional"
        ]:
            if cand in colmap:
                dni_prof_col = colmap[cand]
                break

        # Servicio / prestación
        servicio_col = None
        for cand in [
            "servicio", "prestacion", "prestación", "procedimiento", "descripcion servicio", "descrip. servicio"
        ]:
            if cand in colmap:
                servicio_col = colmap[cand]
                break

        id_serv_col = None
        for cand in ["id servicio", "id_servicio", "idservicio", "cpms", "id procedimiento"]:
            if cand in colmap:
                id_serv_col = colmap[cand]
                break

        if fecha_col is None:
            # Puede que este archivo tenga 1-2 filas de título antes del encabezado real
            # (pasa cuando se exporta/guarda distinto a los demás). Reintentamos corriendo
            # la fila de encabezado antes de rendirnos.
            encontrado_en_reintento = False
            for header_row in (1, 2, 3):
                try:
                    df_retry = pd.read_excel(path, engine="openpyxl", header=header_row)
                except Exception:
                    continue
                if df_retry is None or df_retry.empty:
                    continue
                colmap_retry = detect_columns(df_retry)
                for cand in ["fecha atencion", "fecha de atencion", "fec atencion", "fec. atencion", "fecha", "fecha_atencion"]:
                    if cand in colmap_retry:
                        df = df_retry
                        colmap = colmap_retry
                        fecha_col = colmap_retry[cand]
                        encontrado_en_reintento = True
                        break
                if encontrado_en_reintento:
                    print(f"   ↻ Encontrada leyendo desde la fila {header_row+1} (tenía fila(s) de título arriba del encabezado)")
                    break

        if fecha_col is None:
            columnas_reales = list(df.columns)
            print("   ⚠️ No encuentro columna Fecha Atención en", fn, "-> omito archivo")
            print("      Columnas que sí detecté en este archivo:", columnas_reales)
            print("      Revisa si 'Fecha Atencion' está escrita distinto ahí, o si hay filas de título/resumen arriba del encabezado.")
            continue

        # Vuelve a mapear el resto de columnas por si cambiamos de df en el reintento de arriba
        eess_col = colmap.get("eess") or colmap.get("establecimiento") or colmap.get("ipress") or colmap.get("nombre eess") or colmap.get("establecimieto") or colmap.get("establecimiento de salud") or eess_col
        prof_col = colmap.get("profesional") or colmap.get("nombres profesional") or colmap.get("nombre profesional") or colmap.get("profesional responsable") or colmap.get("responsable atencion") or colmap.get("resp. aten.") or colmap.get("resp aten") or colmap.get("personal") or prof_col
        tipo_col = colmap.get("tipo profesional") or colmap.get("tipo_profesional") or colmap.get("profesion") or colmap.get("tipo personal") or colmap.get("cargo") or tipo_col

        # Recorremos filas
        for _, row in df.iterrows():
            total_rows += 1

            fecha = parse_date_any(row.get(fecha_col))
            if not fecha:
                continue

            anio = int(fecha.year)
            mes = int(fecha.month)
            dia = int(fecha.day)

            eess = "" if eess_col is None else str(row.get(eess_col, "")).strip()
            profesional = "" if prof_col is None else str(row.get(prof_col, "")).strip()
            tipo_prof = "" if tipo_col is None else str(row.get(tipo_col, "")).strip()

            dni_prof = "" if dni_prof_col is None else canon_dni(row.get(dni_prof_col, ""))
            servicio = "" if servicio_col is None else str(row.get(servicio_col, "")).strip()
            id_serv = "" if id_serv_col is None else str(row.get(id_serv_col, "")).strip()

            # Si no hay DNI profesional, igual guardamos (pero ayudará menos para filtro)
            rec = {
                "anio": anio,
                "mes": mes,
                "dia": dia,
                "fecha": fecha.strftime("%Y-%m-%d"),
                "establecimiento": eess,
                "profesional": profesional,
                "tipo_profesional": tipo_prof,
                "dni_prof": dni_prof,      # ✅ DNI del profesional (DNI Resp. Aten.)
                "servicio": servicio,
                "id_servicio": id_serv,
                "source": fn
            }

            buckets.setdefault((anio, mes), []).append(rec)
            used_rows += 1

    # Guardar JSON por mes
    disponibles = []
    ultimo = None

    for (anio, mes), rows in sorted(buckets.items()):
        out_name = f"base_{anio}_{str(mes).zfill(2)}.json"
        out_path = os.path.join(OUT_DIR, out_name)

        # Guardar compacto
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)

        disponibles.append({"anio": anio, "mes": mes, "file": out_name})
        ultimo = {"anio": anio, "mes": mes}

        print(f"✅ Guardado {out_name}  ({len(rows)} registros)")

    # Manifest
    manifest = {
        "disponibles": disponibles,
        "ultimo": ultimo or {"anio": 0, "mes": 0},
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "origen": EXCEL_DIR
    }
    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("\n==========================")
    print("✅ CONSOLIDACIÓN TERMINADA")
    print("Total filas leídas:", total_rows)
    print("Filas usadas:", used_rows)
    print("Meses generados:", len(disponibles))
    print("Salida:", OUT_DIR)
    print("==========================")

if __name__ == "__main__":
    main()
