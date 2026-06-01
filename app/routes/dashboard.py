from flask import Blueprint, render_template
from app.database import get_session
from app.models import Job

bp = Blueprint('dashboard', __name__)

@bp.get('/')
def index():
    session = get_session()
    try:
        jobs = session.query(Job).order_by(Job.created_at.desc()).all()
        jobs_data = []
        for job in jobs:
            p = job.progress()
            jobs_data.append({
                'id': job.id,
                'filename': job.filename,
                'created_at': job.created_at.strftime('%Y-%m-%d %H:%M'),
                'status': job.status,
                'job_type': job.job_type,
                'total': p['total'],
                'done': p['done'],
                'pct': p['pct'],
            })
    finally:
        session.close()
    return render_template('dashboard.html', jobs=jobs_data)
