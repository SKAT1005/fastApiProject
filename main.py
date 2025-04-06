from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from tronpy import Tron

# Конфигурация
DATABASE_URL = "sqlite:///./tron_info.db"  #ЧТобы использовать другую БД, нужно поставить postgresql://user:password@host:port/database_name

PAGINATION_SIZE = 10 # Сколько записей на одной странице

app = FastAPI()
tron = Tron()


engine = create_engine(DATABASE_URL)
Base = declarative_base()

class TronAddressInfo(Base):
    __tablename__ = "tron_address_info"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, index=True)
    bandwidth = Column(Integer)
    energy = Column(Integer)
    balance = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


Base.metadata.create_all(bind=engine)

def get_db():
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield db
    finally:
        db.close()


def get_tron_address_info(address: str) -> Dict[str, Any]:
    """
    Получает информацию об адресе в сети Tron.
    """
    try:
        account = tron.get_account(address)
        bandwidth = account['bandwidth'] if 'bandwidth' in account else 0
        energy = account['energy'] if 'energy' in account else 0
        balance = account['balance'] if 'balance' in account else 0  # Balance in Sun
        return {
            "address": address,
            "bandwidth": bandwidth,
            "energy": energy,
            "balance": balance,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching Tron data: {e}")


@app.post("/address_info/")
def create_address_info(address: str, db: Session = Depends(get_db)):
    """
    Получает и сохраняет информацию об адресе Tron.
    """
    try:
        address_info = get_tron_address_info(address)
        db_record = TronAddressInfo(
            address=address,
            bandwidth=address_info["bandwidth"],
            energy=address_info["energy"],
            balance=address_info["balance"],
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        return address_info
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving to database: {e}")


@app.get("/address_info/", response_model=List[Dict[str, Any]])
def get_address_info_list(
    page: int = Query(1, ge=1), db: Session = Depends(get_db)
):
    """
    Получает список последних запросов информации об адресах Tron с пагинацией.
    """
    offset = (page - 1) * PAGINATION_SIZE
    records = db.query(TronAddressInfo).order_by(TronAddressInfo.created_at.desc()).offset(offset).limit(PAGINATION_SIZE).all()
    return [{"id": record.id,
             "address": record.address,
             "bandwidth": record.bandwidth,
             "energy": record.energy,
             "balance": record.balance,
             "created_at": record.created_at} for record in records]