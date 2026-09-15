import argparse
import asyncio
import json
import sys
from pydantic import ValidationError
from app.config import Settings
from app.database import Database
from app.models.base import Message, ProviderError
from app.models.registry import create_provider


def main() -> None:
    parser = argparse.ArgumentParser(description="Preparação e diagnóstico — Fase 0")
    parser.add_argument("command", choices=["serve", "doctor", "smoke-model"])
    args = parser.parse_args()
    try:
        settings = Settings()
    except ValidationError:
        print("Configuração inválida. Execute scripts/bootstrap.py e confira .env; valores omitidos por segurança.", file=sys.stderr)
        raise SystemExit(2)
    if args.command == "serve":
        import uvicorn
        from app.main import create_app
        uvicorn.run(create_app(settings), host=settings.host, port=settings.port, access_log=False)
        return

    async def check() -> int:
        provider = create_provider(settings)
        try:
            health = await provider.health()
            if args.command == "doctor":
                db = Database(settings.database_path)
                db.initialize()
                db_ok = db.ready()
                print(json.dumps({"database": "ready" if db_ok else "unavailable", "llm": health.model_dump()}, ensure_ascii=False))
                return 0 if db_ok and health.status == "ready" else 1
            if health.status != "ready":
                print(json.dumps(health.model_dump()))
                return 1
            result = await provider.chat([Message(role="user", content="Responda em português, em uma frase: o que é um computador?")])
            # Exibição direta solicitada pelo operador; não grava conteúdo em logs.
            print(result.content)
            return 0
        except ProviderError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        finally:
            await provider.aclose()

    raise SystemExit(asyncio.run(check()))


if __name__ == "__main__":
    main()
