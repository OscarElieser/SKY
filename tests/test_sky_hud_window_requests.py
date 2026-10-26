import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from neural_core import sky_hud_window_requests as w


class HUDWindowRequestTests(unittest.TestCase):
    def test_internal_youtube_and_modes(self):
        self.assertEqual(w.parse_window_request(
            "SKY, ABRE YOUTUBE Y PON LA MUSICA DE JOSEPH EN UNA VENTANA MINI"),
            {"kind":"youtube","query":"joseph","mode":"mini"})
        self.assertEqual(w.parse_window_request(
            "Abre youtube y pon la música de Joseph en una ventana minimizada"),
            {"kind":"youtube","query":"joseph","mode":"minimized"})

    def test_internal_search(self):
        self.assertEqual(w.parse_window_request("Activa el módulo de buscar"),
            {"kind":"search","provider":"web","mode":"normal"})
        self.assertEqual(w.parse_window_request("Abre YouTube"),
            {"kind":"search","provider":"youtube","mode":"normal"})

    def test_window_controls(self):
        self.assertEqual(w.parse_window_request("minimiza el reproductor"),
            {"kind":"window_control","target":"player","mode":"minimized"})
        self.assertEqual(w.parse_window_request("cierra youtube"),
            {"kind":"window_control","target":"player","mode":"close"})

    def test_unrelated_device_commands_unmodified(self):
        self.assertIsNone(w.parse_window_request("abre Microsoft Word"))
        self.assertIsNone(w.parse_window_request("busca mis archivos en Windows"))

    def test_voice_event_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(w, "DB", Path(directory) / "events.db"):
                self.assertEqual(w.latest(), 0)
                n = w.publish({"kind":"youtube","query":"joseph","mode":"mini"})
                self.assertEqual(w.since(0), [{"id":n,"kind":"youtube","target":"","mode":"mini","query":"joseph"}])
                self.assertEqual(w.since(n), [])
                with self.assertRaises(ValueError):
                    w.publish({"kind":"launch_app","mode":"mini"})

    def test_connections_closed_after_database_operations(self):
        """SQLite debe liberar events.db al finalizar, incluso en Windows."""
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(w, "DB", Path(directory) / "connections.db"):
                opened = []
                original_connect = sqlite3.connect

                def track_connect(*args, **kwargs):
                    connection = original_connect(*args, **kwargs)
                    opened.append(connection)
                    return connection

                with patch.object(w.sqlite3, "connect", side_effect=track_connect):
                    self.assertEqual(w.latest(), 0)
                    w.publish({"kind": "youtube", "query": "prueba", "mode": "mini"})
                    self.assertEqual(len(w.since(0)), 1)

                self.assertEqual(len(opened), 3)
                for connection in opened:
                    with self.assertRaises(sqlite3.ProgrammingError):
                        connection.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
