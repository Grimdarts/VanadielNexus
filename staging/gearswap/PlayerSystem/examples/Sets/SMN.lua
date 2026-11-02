return {
    schema = 1,
    kind = "sets",
    job = "SMN",
    definitions = {
        pact_magic = {
            path = {"midcast", "Pet", "MagicalBloodPactRage"},
            slots = {back = {ref = "pact_cape"}},
        },
        pact_accuracy = {
            path = {"midcast", "Pet", "MagicalBloodPactRageAcc"},
            bases = {"pact_magic"},
            slots = {neck = "Sanctity Necklace"},
        },
    },
}
