from sqlalchemy import (String, Boolean, DateTime, Float,
                        Integer, BigInteger, Column, ForeignKey, Table, Enum,
                        UniqueConstraint, TIMESTAMP)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum


CtopiaBase = declarative_base()


class CtopiaMarket(CtopiaBase):
    # stocklook.crypto.cryptopia.api.Cryptopia.get_markets
    __tablename__ = 'ctopia_markets'

    ask_price = Column(Float)
    base_volume = Column(Float)
    bid_price = Column(Float)
    buy_base_volume = Column(Float)
    buy_volume = Column(Float)
    change = Column(Float)
    close = Column(Float)
    high = Column(Float)
    label = Column(String(255))
    last_price = Column(Float)
    low = Column(Float)
    open = Column(Float)
    sell_base_volume = Column(Float)
    sell_volume = Column(Float)
    trade_pair_id = Column(Integer)
    volume = Column(Float)


class CtopiaCurrency(CtopiaBase):
    # stocklook.crypto.cryptopia.api.Cryptopia.get_currencies

    __tablename__ = 'ctopia_currencies'

    algorithm = Column(String(255))
    deposit_confirmations = Column(Integer)
    id = Column(Integer)
    is_tip_enabled = Column(Boolean)
    listing_status = Column(String(255))
    max_withdraw = Column(Float)
    min_base_trade = Column(Float)
    min_tip = Column(Float)
    min_withdraw = Column(Float)
    name = Column(String(255))
    status = Column(String(255))
    status_message = Column(String)
    symbol = Column(String(255))
    withdraw_fee = Column(Float)