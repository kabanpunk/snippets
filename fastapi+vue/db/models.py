from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey, Float

from db.data import Base


class Profile(Base):
    __tablename__ = 'profile'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    a_coefficient = Column(Float, nullable=False)
    b_coefficient = Column(Float, nullable=False)
    c_coefficient = Column(Float, nullable=False)
    description = Column(String, nullable=True)


class PointType(Base):
    __tablename__ = 'point_type'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    color = Column(Integer, nullable=False)
    name = Column(String, nullable=False)


class Point(Base):
    __tablename__ = 'point'
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer(), ForeignKey("profile.id", ondelete='CASCADE'), nullable=False)
    type = Column(Integer(), ForeignKey("point_type.id", ondelete='CASCADE'), nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    seg_y = Column(String)
    processed = Column(Boolean, nullable=True, default=False)


class Estimate(Base):
    __tablename__ = 'estimate'
    id = Column(Integer, primary_key=True)

    profile_id = Column(Integer(), ForeignKey("profile.id", ondelete='CASCADE'), nullable=False)

    source_point_id = Column(Integer(), ForeignKey("point.id", ondelete='CASCADE'), nullable=False)
    receiver_point_id = Column(Integer(), ForeignKey("point.id", ondelete='CASCADE'), nullable=False)

    value = Column(Integer(), nullable=False)

...