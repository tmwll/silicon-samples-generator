import logging
import pandas as pd
import pdfplumber


class PDFLader:

    def extrahiere_text(self, pfad: str) -> str:
        texte = []
        try:
            with pdfplumber.open(pfad) as pdf:
                for page in pdf.pages:
                    try:
                        txt = page.extract_text() or ""
                        if txt:
                            texte.append(txt)
                    except Exception:
                        continue
        except Exception as e:
            logging.warning(f"PDF-Parsing fehlgeschlagen: {pfad} ({e})")

        text = "\n".join(texte)

        return text

    def extrahiere_tabellen(self, pfad: str, zeilen) -> list[str]:
        tabellen: list[str] = []
        try:
            with pdfplumber.open(pfad) as pdf:
                for page in pdf.pages:
                    try:
                        ts = page.extract_tables() or []
                        for t in ts:
                            if t and any(row for row in t):
                                df = pd.DataFrame(t)
                                # if df.shape[0] >= 2:
                                #     df.columns = df.iloc[0].astype(str).values
                                #     df = df.iloc[1:].reset_index(drop=True)

                                if zeilen is None:
                                    df_out = df
                                elif zeilen >= 0:
                                    df_out = df.head(zeilen)
                                else:
                                    df_out = df.tail(
                                        abs(zeilen)
                                    )  # negative Zahl -> letzte N Zeilen

                                tabellen.append(df_out.to_markdown(index=False))
                    except Exception:
                        logging.warning(f"PDF-Parsing fehlgeschlagen: {pfad} ({e})")
                        continue
        except Exception as e:
            logging.warning(f"PDF-Parsing fehlgeschlagen: {pfad} ({e})")
        return tabellen
