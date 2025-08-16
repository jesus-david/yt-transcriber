# Función para escribir transcripciones en formato TXT
def write_txt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(seg["text"].strip() + "\n")
