import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from app.database import get_session
from app.models import Job, Server, get_or_create_settings
from app.services.file_parser import parse_server_file, validate_restart_windows
from app.services.winrm_worker import run_server_worker, run_server_test_worker
from app.executor import get_executor

bp = Blueprint('jobs', __name__)

ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}

@bp.get('/jobs/new')
def new_job_form():
    db = get_session()
    try:
        settings = get_or_create_settings(db)
        from app.services.crypto import decrypt
        default_user = decrypt(settings.default_username_enc) if settings.default_username_enc else ''
    finally:
        db.close()
    return render_template('new_job.html', default_username=default_user)


@bp.post('/jobs/new/preview')
def preview_file():
    if 'file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('jobs.new_job_form'))

    f = request.files['file']
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash(f'Unsupported file type: {ext}. Use .csv or .xlsx', 'danger')
        return redirect(url_for('jobs.new_job_form'))

    upload_dir = os.environ.get('UPLOAD_FOLDER', '/var/lib/winpatch/uploads')
    os.makedirs(upload_dir, mode=0o700, exist_ok=True)
    filename = secure_filename(f.filename)
    filepath = os.path.join(upload_dir, filename)
    f.save(filepath)

    try:
        servers = parse_server_file(filepath)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('jobs.new_job_form'))

    errors = validate_restart_windows(servers)

    return render_template(
        'new_job.html',
        servers=servers,
        errors=errors,
        default_username=request.form.get('default_username', ''),
        filepath=filepath,
        filename=filename,
    )


@bp.post('/jobs/new/start')
def start_job():
    filename = request.form.get('filename', '').strip()
    default_username = request.form.get('default_username', '').strip()
    default_password = request.form.get('default_password', '').strip()

    if not filename:
        flash('No filename provided. Please upload the file again.', 'danger')
        return redirect(url_for('jobs.new_job_form'))

    upload_dir = os.path.realpath(os.environ.get('UPLOAD_FOLDER', '/var/lib/winpatch/uploads'))
    filepath = os.path.realpath(os.path.join(upload_dir, secure_filename(filename)))

    # Confirm the resolved path is within the upload directory (prevent path traversal)
    if not filepath.startswith(upload_dir + os.sep) and filepath != upload_dir:
        flash('Invalid file path.', 'danger')
        return redirect(url_for('jobs.new_job_form'))

    if not os.path.exists(filepath):
        flash('Uploaded file not found. Please upload the file again.', 'danger')
        return redirect(url_for('jobs.new_job_form'))

    try:
        servers = parse_server_file(filepath)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('jobs.new_job_form'))

    db = get_session()
    try:
        job = Job(filename=filename, status='running')
        db.add(job)
        db.flush()

        server_ids = []
        per_server_passwords = {}
        for s in servers:
            record = Server(
                job_id=job.id,
                server_name=s['server_name'],
                ip_address=s['ip_address'],
                restart_window=s['restart_window'],
                username=s['username'],
            )
            db.add(record)
            db.flush()
            server_ids.append(record.id)
            per_server_passwords[record.id] = s['password']

        db.commit()
        job_id = job.id

        settings = get_or_create_settings(db)
        winrm_port = settings.winrm_port
        max_workers = settings.max_workers
    finally:
        db.close()

    executor = get_executor(max_workers)
    for server_id in server_ids:
        executor.submit(
            run_server_worker,
            server_id,
            default_username,
            default_password,
            per_server_passwords.get(server_id),
            winrm_port,
        )

    flash(f'Job started for {len(server_ids)} servers.', 'success')
    return redirect(url_for('jobs.job_detail', job_id=job_id))


@bp.get('/jobs/<int:job_id>')
def job_detail(job_id):
    db = get_session()
    try:
        job = db.get(Job, job_id)
        if not job:
            flash('Job not found.', 'danger')
            return redirect(url_for('dashboard.index'))
        servers = [s.to_dict() for s in job.servers]
        progress = job.progress()
        created_at = job.created_at
        filename = job.filename
        job_type = job.job_type
    finally:
        db.close()
    return render_template('job_detail.html', job_id=job_id,
                           filename=filename, servers=servers,
                           progress=progress, created_at=created_at,
                           job_type=job_type)


@bp.post('/jobs/new/test')
def test_job():
    filename = request.form.get('filename', '').strip()
    default_username = request.form.get('default_username', '').strip()
    default_password = request.form.get('default_password', '').strip()

    if not filename:
        flash('No filename provided. Please upload the file again.', 'danger')
        return redirect(url_for('jobs.new_job_form'))

    upload_dir = os.path.realpath(os.environ.get('UPLOAD_FOLDER', '/var/lib/winpatch/uploads'))
    filepath = os.path.realpath(os.path.join(upload_dir, secure_filename(filename)))

    if not filepath.startswith(upload_dir + os.sep) and filepath != upload_dir:
        flash('Invalid file path.', 'danger')
        return redirect(url_for('jobs.new_job_form'))

    if not os.path.exists(filepath):
        flash('Uploaded file not found. Please upload the file again.', 'danger')
        return redirect(url_for('jobs.new_job_form'))

    try:
        servers = parse_server_file(filepath)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('jobs.new_job_form'))

    db = get_session()
    try:
        job = Job(filename=filename, status='running', job_type='test')
        db.add(job)
        db.flush()

        server_ids = []
        per_server_passwords = {}
        for s in servers:
            record = Server(
                job_id=job.id,
                server_name=s['server_name'],
                ip_address=s['ip_address'],
                restart_window=s['restart_window'],
                username=s['username'],
            )
            db.add(record)
            db.flush()
            server_ids.append(record.id)
            per_server_passwords[record.id] = s['password']

        db.commit()
        job_id = job.id

        settings = get_or_create_settings(db)
        winrm_port = settings.winrm_port
        max_workers = settings.max_workers
    finally:
        db.close()

    executor = get_executor(max_workers)
    for server_id in server_ids:
        executor.submit(
            run_server_test_worker,
            server_id,
            default_username,
            default_password,
            per_server_passwords.get(server_id),
            winrm_port,
        )

    flash(f'Test job started for {len(server_ids)} servers.', 'success')
    return redirect(url_for('jobs.job_detail', job_id=job_id))
