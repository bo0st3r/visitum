from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class City(Base):
    __tablename__ = 'cities'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    population = Column(Integer, nullable=True) # Allow null temporarily if population fetch fails

    museums = relationship("Museum", back_populates="city") # Defines the one-to-many relationship

    # Add a unique constraint for the combination of country and name.
    # The order ('country', 'name') is chosen because queries are likely
    # to filter by country first, allowing the database index to be used efficiently.
    __table_args__ = (UniqueConstraint('country', 'name', name='_city_name_country_uc'),)

    def __repr__(self):
        return f"<City(id={self.id}, name='{self.name}', country='{self.country}', population={self.population})>"


class Museum(Base):
    __tablename__ = 'museums'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    visitors_count = Column(Integer, nullable=False)
    visitors_year = Column(Integer, nullable=False)
    city_id = Column(Integer, ForeignKey('cities.id'), nullable=False) # Foreign key constraint

    city = relationship("City", back_populates="museums") # Defines the many-to-one relationship
    # Add a unique constraint for the combination of city_id, visitors_year, and name.
    # The order ('city_id', 'visitors_year', 'name') is chosen to optimize
    # for common query patterns, such as finding all museums in a specific city,
    # or all museums in a specific city for a given year.
    __table_args__ = (UniqueConstraint('city_id', 'visitors_year', 'name', name='_museum_city_id_name_visitors_year_uc'),)

    def __repr__(self):
        return f"<Museum(id={self.id}, name='{self.name}', visitors={self.visitors_count} ({self.visitors_year}), city_id={self.city_id})>"

