import time
import logging

LOG = logging.getLogger(__name__)

def retry( max_retries=1, delay=0, backoff=2,throw_immediately=False, logger=None):
    if logger is None:
        logger = LOG
    def default_filter(r):
        return True
    def deco_retry(f, error_filter=default_filter):
        mtries, mdelay = max_retries, delay
        r = None
        while mtries > 0:
            try:
                r = f()
                if error_filter(r):
                    return r
                else:
                    logger.warn("%s run error in %s time, retry in %s seconds..." % (f, max_retries - mtries + 1, mdelay))
                    time.sleep(mdelay)
            except:
                if throw_immediately or mtries == 1:
                    raise
                import sys
                import traceback
                exc_type, exc_value, exc_traceback = sys.exc_info()
                lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                logger.warn('%s run except in %s time, retry in %s seconds..., exception: %s ' % (f, max_retries - mtries + 1, mdelay, "".join(lines)))
                time.sleep(mdelay)
            finally:
                mtries -= 1
                mdelay *= backoff
        return r
    return deco_retry