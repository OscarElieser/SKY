"""Run SKY media renders in a dedicated process, outside the HTTP API.

Set SKY_CREATIVE_WORKER=0 in the API process. Start this process alongside it.
Runs only approved queued renders. A crashed job is marked needs_review.
"""
import logging,signal,time
from neural_core.sky_creative import run_next_job,mark_interrupted

STOP=False

def stop(*_):
    global STOP
    STOP=True


def main():
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    mark_interrupted()
    while not STOP:
        job=None
        try:
            job=run_next_job()
            if job:logging.info('Render %s status=%s',job.get('id','?'),job['status'])
        except Exception:
            # Never print secrets, project instructions or the input path.
            logging.exception('Error del worker; requiere revisión privada')
        if not job:
            time.sleep(2)
    logging.info('SKY worker detenido')

if __name__=='__main__':main()
