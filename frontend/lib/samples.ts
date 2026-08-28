import type { ApplicationInput } from "./api";

export const SAMPLES: { id: string; label: string; input: ApplicationInput }[] = [
  {
    id: "de-hp-14",
    label: "DE · 14 kW heat pump",
    input: {
      country: "DE",
      applicant_name: "Anna Schmidt",
      address: "Lindenstraße 12, 50674 Köln",
      description:
        "Installing an air-source heat pump, Vaillant aroTHERM plus, 14 kW electrical rating. Requesting grid connection.",
      documents: [
        "application_form",
        "heat_pump_datasheet",
        "electrician_confirmation",
      ],
    },
  },
  {
    id: "at-hp-14",
    label: "AT · same 14 kW request",
    input: {
      country: "AT",
      applicant_name: "Anna Schmidt",
      address: "Lindenstraße 12, 50674 Köln",
      description:
        "Installing an air-source heat pump, Vaillant aroTHERM plus, 14 kW electrical rating. Requesting grid connection.",
      documents: [
        "application_form",
        "heat_pump_datasheet",
        "electrician_confirmation",
      ],
    },
  },
  {
    id: "de-ev-missing",
    label: "DE · EV charger, missing docs",
    input: {
      country: "DE",
      applicant_name: "Miriam Fischer",
      address: "Gartenweg 8, 10115 Berlin",
      description:
        "Requesting connection for a 22 kW wallbox EV charger in our garage.",
      documents: ["application_form", "charger_datasheet"],
    },
  },
  {
    id: "de-pv-over",
    label: "DE · 120 kW solar, over limit",
    input: {
      country: "DE",
      applicant_name: "AgrarEnergie GmbH",
      address: "Industriestraße 2, 04103 Leipzig",
      description: "Commercial rooftop PV plant, 120 kW feed-in requested.",
      documents: [
        "application_form",
        "pv_datasheet",
        "installer_certificate",
        "site_plan",
      ],
    },
  },
];
