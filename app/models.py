from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class Job(Base):
    __tablename__ = 'jobs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), default='pending')

    servers: Mapped[list['Server']] = relationship(
        'Server', back_populates='job', cascade='all, delete-orphan'
    )

    def progress(self) -> dict:
        total = len(self.servers)
        if total == 0:
            return {'total': 0, 'done': 0, 'pct': 0}
        done = sum(1 for s in self.servers if s.status in (
            'up_to_date', 'restart_scheduled', 'error'
        ))
        return {'total': total, 'done': done, 'pct': int(done / total * 100)}


class Server(Base):
    __tablename__ = 'servers'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey('jobs.id'), nullable=False)
    server_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    restart_window: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(100), default='pending')
    updates_installed: Mapped[int] = mapped_column(Integer, default=0)
    restart_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    log_output: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job: Mapped['Job'] = relationship('Job', back_populates='servers')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'server_name': self.server_name,
            'ip_address': self.ip_address,
            'restart_window': self.restart_window,
            'status': self.status,
            'updates_installed': self.updates_installed,
            'restart_scheduled_at': self.restart_scheduled_at.isoformat() if self.restart_scheduled_at else None,
            'error_message': self.error_message,
        }


class AppSettings(Base):
    __tablename__ = 'app_settings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    default_username_enc: Mapped[str | None] = mapped_column(String(512))
    default_password_enc: Mapped[str | None] = mapped_column(String(512))
    winrm_port: Mapped[int] = mapped_column(Integer, default=5985)
    max_workers: Mapped[int] = mapped_column(Integer, default=10)


def get_or_create_settings(session) -> AppSettings:
    settings = session.get(AppSettings, 1)
    if not settings:
        settings = AppSettings(id=1, winrm_port=5985, max_workers=10)
        session.add(settings)
        session.commit()
    return settings
