"""SKY Universal: servicios privados, sin ejecución financiera automática."""
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass
