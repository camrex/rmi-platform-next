import re

from pydantic import BaseModel, ConfigDict


class Ref(BaseModel):
    """
    A stable reference to a linkable entity.

    Forms:
    - `gis:<dataset>:<GlobalID>`
    - `oid:<dataset>:<OBJECTID>`
    - `<module>.<kind>:<id>`
    - `catalog.item:<id>`
    - `pricing.price:<id>`
    """

    model_config = ConfigDict(frozen=True)

    scheme: str
    value: str

    def __str__(self) -> str:
        return f"{self.scheme}:{self.value}"

    def __repr__(self) -> str:
        return f"Ref({self.__str__()!r})"

    @classmethod
    def parse(cls, s: str) -> "Ref":
        if not s:
            raise ValueError("Ref string cannot be empty")
        if ":" not in s:
            raise ValueError(f"Malformed ref: {s}. Expected format 'scheme:value'")

        scheme, value = s.split(":", 1)
        if not scheme or not value:
            raise ValueError(f"Malformed ref: {s}. Scheme and value must both be present")

        if scheme in ("gis", "oid"):
            if ":" not in value:
                raise ValueError(
                    f"Malformed {scheme} ref: {s}. Expected format '{scheme}:dataset:id'"
                )
            dataset, identifier = value.split(":", 1)
            if not dataset or not identifier:
                raise ValueError(
                    f"Malformed {scheme} ref: {s}. Dataset and identifier must both be present"
                )
        elif not re.match(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$", scheme):
            raise ValueError(f"Invalid scheme: {scheme}. Expected 'gis', 'oid', or '<key>.<kind>'")

        return cls(scheme=scheme, value=value)

    @property
    def dataset(self) -> str | None:
        """Returns the dataset for gis and oid refs, otherwise None."""
        if self.scheme in ("gis", "oid"):
            return self.value.split(":", 1)[0]
        return None

    @property
    def identifier(self) -> str:
        """Returns the unique identifier within the scheme (and dataset if applicable)."""
        if self.scheme in ("gis", "oid"):
            return self.value.split(":", 1)[1]
        return self.value
