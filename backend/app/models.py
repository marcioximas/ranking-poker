from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class Config(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True, default=1)
    tournament_name = Column(String, default="Poker Night")
    buyin_value = Column(Float, default=50.0)
    addon_value = Column(Float, default=50.0)
    presence_points = Column(Integer, default=10)
    punctuality_points = Column(Integer, default=15)
    itm_bonus_points = Column(Integer, default=5)
    prize_pct = Column(Float, default=70.0)
    ranking_pct = Column(Float, default=30.0)
    pix_receiver_player_id = Column(Integer, nullable=True)


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    telefone = Column(String, nullable=True)
    pix = Column(String, nullable=True)

    round_entries = relationship("RoundPlayer", back_populates="player", cascade="all, delete-orphan")
    semestral_scores = relationship("SemestralScore", back_populates="player", cascade="all, delete-orphan")


class Round(Base):
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String, nullable=False)
    date = Column(Date, nullable=True)
    is_active_in_ranking = Column(Boolean, default=True)
    is_current = Column(Boolean, default=False)
    is_finalized = Column(Boolean, default=False)

    round_players = relationship("RoundPlayer", back_populates="round", cascade="all, delete-orphan")
    semestral_scores = relationship("SemestralScore", back_populates="round", cascade="all, delete-orphan")


class RoundPlayer(Base):
    __tablename__ = "round_players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    round_id = Column(Integer, ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    buyin = Column(Integer, default=1)
    addon = Column(Integer, default=0)
    colocacao = Column(Integer, default=0)
    pontos = Column(Integer, default=0)
    presenca = Column(Integer, default=0)
    bonus = Column(Integer, default=0)
    indicacao = Column(Integer, default=0)
    pontualidade = Column(Integer, default=0)

    round = relationship("Round", back_populates="round_players")
    player = relationship("Player", back_populates="round_entries")

    __table_args__ = (UniqueConstraint("round_id", "player_id"),)


class SemestralScore(Base):
    __tablename__ = "semestral_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    round_id = Column(Integer, ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, default=0)

    player = relationship("Player", back_populates="semestral_scores")
    round = relationship("Round", back_populates="semestral_scores")

    __table_args__ = (UniqueConstraint("player_id", "round_id"),)


class Financial(Base):
    __tablename__ = "financial"

    id = Column(Integer, primary_key=True, default=1)
    caixa_anterior = Column(Float, default=3868.23)
    ranking_anterior = Column(Float, default=1621.25)


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(Float, default=0.0)
