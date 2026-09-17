from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 Declarative Base Class.
    Automatically generates __tablename__ from class name in lowercase.
    """
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
