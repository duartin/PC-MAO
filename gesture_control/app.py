"""Application entry point for the Qt hand-gesture interface."""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Controle do computador por gestos")
    parser.add_argument("--camera", type=int, default=0, help="índice da webcam (padrão: 0)")
    parser.add_argument("--motion-sensitivity", type=float, default=1.0,
                        help="sensibilidade dos deslizes entre 0.5 e 2.0 (padrão: 1.0)")
    parser.add_argument("--execute", action="store_true",
                        help="abre a interface com ações reais habilitadas")
    args = parser.parse_args()
    if not 0.5 <= args.motion_sensitivity <= 2.0:
        parser.error("--motion-sensitivity deve estar entre 0.5 e 2.0")

    try:
        from .main_window import launch
    except ImportError as exc:
        parser.error(f"Dependência da interface ausente. Instale requirements.txt. Detalhe: {exc}")
    raise SystemExit(launch(args.camera, args.motion_sensitivity, args.execute))


if __name__ == "__main__":
    main()
