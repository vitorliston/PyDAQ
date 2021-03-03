def logic(T_ff,T_fz,logic_vars,only_fz,compressor_ison,logic=2):
    if logic==1:
        if T_fz > logic_vars['fz_max'] + 7 or T_ff > logic_vars['ff_max'] + 7:
            pulldown = True
        else:
            pulldown = False

        if T_fz <= logic_vars['fz_min']:

            only_fz = False
            compressor_ison = T_ff > logic_vars['ff_max'] - logic_vars['ff_tol']

        elif T_fz >= logic_vars['fz_max']:

            only_fz = logic_vars['ff_max'] - T_ff >= logic_vars['ff_tol']
            compressor_ison = True


        elif T_ff <= logic_vars['ff_min']:

            only_fz = T_fz >= logic_vars['fz_max']
            compressor_ison = only_fz

        elif T_ff >= logic_vars['ff_max']:

            only_fz = False
            compressor_ison = True

    elif logic==2:

        if T_fz > logic_vars['fz_max'] + 7 or T_ff > logic_vars['ff_max'] + 7:
            pulldown = True
        else:
            pulldown = False



        if T_ff <= logic_vars['ff_min']:
            print(1)
            only_fz = True
            compressor_ison = T_fz >= logic_vars['fz_min']

        elif T_ff >= logic_vars['ff_max']:
            print(2)
            only_fz = False
            compressor_ison = True

        elif T_fz <= logic_vars['fz_min']:
            print(3)
            compressor_ison = T_ff >= logic_vars['ff_max']
            only_fz = False

    return [only_fz,compressor_ison,pulldown]