

__author__ = 'jacurran'

##################################################

def get_key(hostname,hw_pid,sup_pid):
    """
    Determine Python App Key.
    Will use this to query the Standards Excel for applicable IOS filenames.
    """

    Maestro_key = ""

    if sup_pid:
        if sup_pid in ["WS-X45-SUP8-E"]:
            Maestro_key = "WS-X45-SUP8-E"

        elif sup_pid in ["WS-X45-SUP7-E"]:
            Maestro_key = "WS-X45-SUP7-E"

        elif sup_pid in ["NPE-G1"]:
            Maestro_key = "NPE-G1"

        elif sup_pid in ["NPE-G2"]:
            Maestro_key = "NPE-G2"

        elif sup_pid in ["ASR1000-RP1",
                         "ASR1002-RP1"]:
            Maestro_key = "ASR1000-RP1"

        elif sup_pid in ["ASR1000-RP2"]:
            Maestro_key = "ASR1000-RP2"

        elif sup_pid in ["VS-SUP2T-10G"] \
                and "***" in hostname \
                and "***" in hostname:
            Maestro_key = "VS-SUP2T-10G-WLGW"

        elif sup_pid in ["VS-SUP2T-10G"]:
            Maestro_key = "VS-SUP2T-10G"

        elif sup_pid in ["WS-SUP32-GE-3B"]:
            Maestro_key = "WS-SUP32-GE-3B"

        elif sup_pid in ["WS-SUP720-3B",
                         "VS-S720-10G",
                         "WS-SUP720-3BXL"] \
                and "***" in hostname \
                and "***" in hostname:
            Maestro_key = "SUP720-WLGW"

        elif sup_pid in ["WS-SUP720-3B",
                         "VS-S720-10G",
                         "WS-SUP720-3BXL"] \
                and "***" in hostname:
            Maestro_key = "SUP720-SW"

        elif sup_pid in ["WS-SUP720-3B",
                         "VS-S720-10G",
                         "WS-SUP720-3BXL"] \
                and "***" in hostname:
            Maestro_key = "SUP720-DMVPN"

        elif sup_pid in ["WS-SUP720-3B",
                         "VS-S720-10G",
                         "WS-SUP720-3BXL"] \
                and "***" in hostname:
            Maestro_key = "SUP720-GW"

    elif not sup_pid:
        if hw_pid in ["C6880-X"]:
            Maestro_key = "C6880"

        elif hw_pid in ["3845",
                        "CISCO3845"]:
            Maestro_key = "CISCO3845"

        elif hw_pid in ["ISR4451-X/K9"]:
            Maestro_key = "ISR4451"

        elif hw_pid in ["IE-3010-16S-8PC"]:
            Maestro_key = "IE-3010"

        elif hw_pid in ["WS-C4500X-16",
                        "WS-C4500X-32"]:
            Maestro_key = "C4500X"

        elif hw_pid in ["WS-C4900M",
                        "WS-C4948E",
                        "WS-C4948E-F"]:
            Maestro_key = "C49XX-ME"

        elif hw_pid in ["CISCO3945-CHASSIS"] \
                and not "***" in hostname:
            Maestro_key = "CISCO3945"

        elif hw_pid in ["CISCO3945-CHASSIS"] \
                and "***" in hostname:
            Maestro_key = "CISCO3945-CVP"

        elif hw_pid in ["CISCO2901/K9"]:
            Maestro_key = "CISCO2901"

        elif hw_pid in ["CISCO2911/K9"]:
            Maestro_key = "CISCO2911"

        elif hw_pid in ["WS-C3750E-24TD-E",
                        "WS-C3750E-48PD-EF",
                        "WS-C3750E-48PD-SF",
                        "WS-C3750X-24P-S",
                        "WS-C3750X-24S-S",
                        "WS-C3750X-24T-S",
                        "WS-C3750X-24T-L",
                        "WS-C3750X-48P-L",
                        "WS-C3750X-48P-S",
                        "WS-C3750X-48T-S",
                        "WS-C3750X-48PF-E",
                        "WS-C3750X-48PF-L",
                        "WS-C3750X-48PF-S"]:
            Maestro_key = "C3750EX"

        elif hw_pid in ["WS-C3750-24PS-S",
                        "WS-C3750-48PS-S",
                        "WS-C3750G-12S-S",
                        "WS-C3750G-24PS-S",
                        "WS-C3750G-24PS-E",
                        "WS-C3750G-24TS-S1U",
                        "WS-C3750G-48PS-S",
                        "WS-C3750G-48PS-E",
                        "WS-C3750G-48TS-S"]:
            Maestro_key = "C3750-G"

        elif hw_pid in ["WS-C3560-12PC-S"]:
            Maestro_key = "WS-C3560-12PC-S"

        elif hw_pid in ["CISCO2951/K9"]:
            Maestro_key = "CISCO2951"

        elif hw_pid in ["2611XM"]:
            Maestro_key = "2611XM"

        elif hw_pid in ["CISCO2811",
                        "2811"]:
            Maestro_key = "CISCO2811"

        elif hw_pid in ["SM-ES3G-16-P",
                        "SM-ES3G-24-P"]:
            Maestro_key = "SM-ES3G"

        elif hw_pid in ["WS-C3850-48P",
                        "WS-C3850-48U"] \
                and "***" in hostname:
            Maestro_key = "C3850CL"

        elif hw_pid in ["WS-C3850-48P",
                        "WS-C3850-48U"]:
            Maestro_key = "C3850W"

        elif hw_pid in ["CISCO891W-AGN-A-K9",
                        "CISCO892W-AGN-E-K9"]:
            Maestro_key = "CISCO890"

        elif hw_pid in ["WS-C4948",
                        "WS-C4948-10GE"]:
            Maestro_key = "WS-C4948-XX"

    return Maestro_key

    ##################################################