from logging import Logger, LogRecord

import coloredlogs


class ExtraFormatter(coloredlogs.ColoredFormatter):
    FMT = '%(asctime)s %(levelname)s %(message)s %(extra_fields)s'
    BUILTIN_KEYS = {
        *LogRecord('', 0, '', 0, '', [], None).__dict__.keys(),
        "_extra"
    }

    def format(self, record):
        extra = {k: v for k, v in record.__dict__.items() if k not in self.BUILTIN_KEYS}
        record.extra_fields = ' '.join(f'{k}={v!r}' for k, v in extra.items())
        return super().format(record)

    @staticmethod
    def install(logger: Logger, level: str):
        logger.setLevel(level)
        logger.handlers[0].setFormatter(ExtraFormatter(ExtraFormatter.FMT))
