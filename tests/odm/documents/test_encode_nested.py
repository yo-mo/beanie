from beanie.odm.utils.dump import get_dict
from tests.odm.models import Inner, DocumentWithNestedField


async def test_simple_case():
    inner = Inner(num_1=1)
    doc = DocumentWithNestedField(num_2=2, inner=inner)
    assert doc.inner is inner

    data = get_dict(doc)
    assert data[0][0]["object"].inner is data[1][0]["object"]

    inner.num_1 = 100
    await doc.insert()
    # assert doc == 1

    inner.num_1 = 200

    await doc.replace()

