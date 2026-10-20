"""Compatibility adapter for Excel testing using openpyxl."""
import openpyxl

class Blob:
    def __init__(self, path: str):
        self.path = path

    @classmethod
    def load(cls, path: str):
        return cls(path)

class _WorksheetWrapper:
    def __init__(self, ws):
        self._ws = ws

    def get_range(self, cell_range: str):
        cells = self._ws[cell_range]
        class _Range:
            def __init__(self, c):
                if isinstance(c, tuple):
                    if len(c) > 0 and isinstance(c[0], tuple):
                        self.values = [[cell.value for cell in row] for row in c]
                    else:
                        self.values = [[cell.value for cell in c]]
                else:
                    self.values = [[c.value]]
        return _Range(cells)

class _WorksheetsWrapper:
    def __init__(self, wb):
        self._wb = wb

    def get_item_at(self, idx: int):
        return _WorksheetWrapper(self._wb.worksheets[idx])

class SpreadsheetFile:
    def __init__(self, wb):
        self.worksheets = _WorksheetsWrapper(wb)

    @classmethod
    def import_xlsx(cls, blob: Blob):
        wb = openpyxl.load_workbook(blob.path)
        return cls(wb)
