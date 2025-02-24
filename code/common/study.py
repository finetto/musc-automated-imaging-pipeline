import random

# generate deidentified ID that is different from already used IDs
def generate_deidentified_id(used_ids=(), prefix="M", digits=3, max_attempts=100000):
    
    n_attempts=0
    deidentified_id = None
    
    # get ID parameters
    min_id = 10**(digits-1) # according to provided specs, ID should not start with zero
    max_id = 10**digits -1
    id_format = "{:0" + str(digits) + "d}"
    
    # search for new unique id
    while (deidentified_id==None) or (deidentified_id in used_ids):
        n_attempts = n_attempts+1
        if n_attempts > max_attempts:
            deidentified_id = None
            break
        
        deidentified_id = prefix + id_format.format(random.randrange(min_id, max_id+1))
        
    return deidentified_id