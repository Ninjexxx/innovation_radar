import logging

from innovation_radar.logging_config import HANDLER_NAME, configure_logging


def test_basic_logging_is_configured_once(capsys) -> None:
    logger = configure_logging("DEBUG")

    try:
        first_handlers = [
            handler for handler in logger.handlers if handler.name == HANDLER_NAME
        ]
        configure_logging("INFO")
        second_handlers = [
            handler for handler in logger.handlers if handler.name == HANDLER_NAME
        ]

        logger.info("foundation ready")

        assert logger.level == logging.INFO
        assert len(first_handlers) == 1
        assert second_handlers == first_handlers
        assert "foundation ready" in capsys.readouterr().err
    finally:
        for handler in list(logger.handlers):
            if handler.name == HANDLER_NAME:
                logger.removeHandler(handler)
                handler.close()
