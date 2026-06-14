# --------------------------------------------------------------
# services: business logic for the STAKEHOLDERS resource (read-only).
# Stakeholders are the known talking entities (the `stakeholders` collection).
# Keeps main.py thin (routing/validation only); the Mongo reads live here.
# --------------------------------------------------------------
from bunnet import PydanticObjectId

from lib.core.models import TKMemoryStakeholdersDoc


# --- domain errors (mapped by the API layer onto HTTP codes) ---
class InvalidStakeholderIdError(Exception):
    """The provided object id is not a valid ObjectId."""

class StakeholderNotFoundError(Exception):
    """No stakeholder found for the given object id."""


class StakeholderService:
    """Read-only access to stakeholders (the 'stakeholders' collection).

    Only reads, so it needs no pipeline dependencies: the API layer builds a
    single instance at startup and reuses it for every request.
    """

    # fetch a stakeholder by id, or raise a domain error
    def _resolve(self, object_id: str) -> TKMemoryStakeholdersDoc:
        try:
            oid = PydanticObjectId(object_id)
        except Exception as error:
            raise InvalidStakeholderIdError(object_id) from error
        stakeholder = TKMemoryStakeholdersDoc.get(oid).run()  # bunnet: get() returns a query, must be executed with run()
        if stakeholder is None:
            raise StakeholderNotFoundError(object_id)
        return stakeholder

    # list stakeholders; optional projection (e.g. a summary view)
    def list(self, projection=None):
        cursor = TKMemoryStakeholdersDoc.find({})
        if projection is not None:
            cursor = cursor.project(projection)
        return cursor.to_list()

    # single stakeholder (full document)
    def get(self, object_id: str) -> TKMemoryStakeholdersDoc:
        return self._resolve(object_id)
