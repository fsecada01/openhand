"""Seed rows for the `DisabilityCondition` reference table.

Sourced directly from SSA's official "Blue Book" (Listing of
Impairments) — Adult Listings, Part A
(https://www.ssa.gov/disability/professionals/bluebook/AdultListings.htm)
and Childhood Listings, Part B
(https://www.ssa.gov/disability/professionals/bluebook/ChildhoodListings.htm).
Every adult listing (sections 1.00-14.00; 9.00 Endocrine has none of
its own — SSA evaluates endocrine effects under the other body
systems) is represented once. Childhood (Part B) listings are only
added as separate rows where they cover something with no adult
counterpart (e.g. low birth weight, failure to thrive, developmental
delay in infants/toddlers) — sections where Part B simply mirrors
Part A by name reuse the adult row instead of duplicating it.

Reference data, not individual records, and not authoritative on its
own (SSA still decides any real claim). Each row:
(name, category, aliases, ssa_reference).
"""

DISABILITY_CONDITIONS = [
    # --- 1.00 Musculoskeletal Disorders --------------------------------
    (
        "Disorders of the skeletal spine resulting in compromise of a "
        "nerve root(s)",
        "physical",
        "pinched nerve in spine,herniated disc,spinal nerve root "
        "compression,sciatica,radiculopathy,degenerative disc",
        "SSA Blue Book 1.15",
    ),
    (
        "Lumbar spinal stenosis resulting in compromise of the cauda equina",
        "physical",
        "spinal stenosis,lower back stenosis,cauda equina syndrome,"
        "narrowing of spinal canal",
        "SSA Blue Book 1.16",
    ),
    (
        "Reconstructive surgery or surgical arthrodesis of a major "
        "weight-bearing joint",
        "physical",
        "joint fusion surgery,hip or knee reconstruction,joint "
        "replacement recovery,spinal fusion",
        "SSA Blue Book 1.17",
    ),
    (
        "Abnormality of a major joint(s) in any extremity",
        "physical",
        "arthritis,joint deformity,severe joint damage,hip or knee problems",
        "SSA Blue Book 1.18",
    ),
    (
        "Pathologic fractures due to any cause",
        "physical",
        "bone fractures from disease,brittle bone fractures,"
        "osteoporosis fractures,repeated broken bones",
        "SSA Blue Book 1.19",
    ),
    (
        "Amputation due to any cause",
        "physical",
        "amputation,loss of limb,missing arm or leg",
        "SSA Blue Book 1.20",
    ),
    (
        "Soft tissue injury or abnormality under continuing surgical "
        "management",
        "physical",
        "severe soft tissue injury,ongoing wound care,skin graft "
        "recovery,crush injury",
        "SSA Blue Book 1.21",
    ),
    (
        "Non-healing or complex fracture of the femur, tibia, pelvis, "
        "or talocrural bones",
        "physical",
        "broken leg won't heal,non-union fracture,complex leg or "
        "pelvis fracture,ankle fracture",
        "SSA Blue Book 1.22",
    ),
    (
        "Non-healing or complex fracture of an upper extremity",
        "physical",
        "broken arm won't heal,non-union arm fracture,complex wrist "
        "or shoulder fracture",
        "SSA Blue Book 1.23",
    ),
    (
        "Musculoskeletal disorders of infants and toddlers with "
        "developmental motor delay",
        "physical",
        "motor delay baby,not crawling or walking on time,delayed "
        "gross motor skills toddler",
        "SSA Blue Book 101.24 (Childhood Listings, Part B)",
    ),
    # --- 2.00 Special Senses and Speech ---------------------------------
    (
        "Loss of central visual acuity",
        "physical",
        "legal blindness,severe vision loss,low vision,can't see clearly,blind",
        "SSA Blue Book 2.02",
    ),
    (
        "Contraction of the visual fields in the better eye",
        "physical",
        "tunnel vision,peripheral vision loss,narrow field of vision",
        "SSA Blue Book 2.03",
    ),
    (
        "Loss of visual efficiency",
        "physical",
        "combined vision loss,poor visual function,low vision",
        "SSA Blue Book 2.04",
    ),
    (
        "Disturbance of labyrinthine-vestibular function",
        "physical",
        "chronic vertigo,balance disorder,meniere's disease,dizziness disorder",
        "SSA Blue Book 2.07",
    ),
    (
        "Loss of speech",
        "physical",
        "unable to speak,loss of voice,speech impairment",
        "SSA Blue Book 2.09",
    ),
    (
        "Hearing loss not treated with cochlear implantation",
        "physical",
        "deafness,severe hearing loss,hard of hearing,deaf",
        "SSA Blue Book 2.10",
    ),
    (
        "Hearing loss treated with cochlear implantation",
        "physical",
        "cochlear implant,deaf child with implant",
        "SSA Blue Book 102.11 (Childhood Listings, Part B)",
    ),
    # --- 3.00 Respiratory Disorders --------------------------------------
    (
        "Chronic respiratory disorders",
        "physical",
        "copd,chronic obstructive pulmonary disease,chronic lung "
        "disease,emphysema,chronic bronchitis",
        "SSA Blue Book 3.02",
    ),
    (
        "Asthma",
        "physical",
        "asthma,severe asthma attacks,reactive airway disease",
        "SSA Blue Book 3.03",
    ),
    (
        "Cystic fibrosis",
        "physical",
        "cystic fibrosis,cf",
        "SSA Blue Book 3.04",
    ),
    (
        "Bronchiectasis",
        "physical",
        "bronchiectasis,chronic lung infections",
        "SSA Blue Book 3.07",
    ),
    (
        "Chronic pulmonary hypertension due to any cause",
        "physical",
        "pulmonary hypertension,high blood pressure in lungs",
        "SSA Blue Book 3.09",
    ),
    (
        "Lung transplant",
        "physical",
        "lung transplant,post-transplant lung recovery",
        "SSA Blue Book 3.11",
    ),
    (
        "Respiratory failure",
        "physical",
        "respiratory failure,breathing failure,ventilator dependence",
        "SSA Blue Book 3.14",
    ),
    (
        "Growth failure due to any chronic respiratory disorder",
        "physical",
        "not gaining weight from lung disease,failure to thrive from "
        "breathing problems,oxygen-dependent growth failure",
        "SSA Blue Book 103.06 (Childhood Listings, Part B)",
    ),
    # --- 4.00 Cardiovascular System --------------------------------------
    (
        "Chronic heart failure",
        "physical",
        "congestive heart failure,chf,heart failure,cardiomyopathy",
        "SSA Blue Book 4.02",
    ),
    (
        "Ischemic heart disease",
        "physical",
        "coronary artery disease,heart disease,angina",
        "SSA Blue Book 4.04",
    ),
    (
        "Recurrent arrhythmias",
        "physical",
        "irregular heartbeat,arrhythmia,atrial fibrillation",
        "SSA Blue Book 4.05",
    ),
    (
        "Symptomatic congenital heart disease",
        "physical",
        "congenital heart defect,born with heart problem,congenital "
        "heart disease",
        "SSA Blue Book 4.06",
    ),
    (
        "Heart transplant",
        "physical",
        "heart transplant,post-transplant heart recovery",
        "SSA Blue Book 4.09",
    ),
    (
        "Aneurysm of aorta or major branches",
        "physical",
        "aortic aneurysm,artery aneurysm",
        "SSA Blue Book 4.10",
    ),
    (
        "Chronic venous insufficiency",
        "physical",
        "venous insufficiency,chronic leg swelling,varicose vein complications",
        "SSA Blue Book 4.11",
    ),
    (
        "Peripheral arterial disease",
        "physical",
        "pad,poor circulation in legs,peripheral artery disease",
        "SSA Blue Book 4.12",
    ),
    (
        "Rheumatic heart disease",
        "physical",
        "rheumatic fever heart damage,rheumatic heart disease",
        "SSA Blue Book 104.13 (Childhood Listings, Part B)",
    ),
    # --- 5.00 Digestive Disorders -----------------------------------------
    (
        "Gastrointestinal hemorrhaging requiring blood transfusions",
        "physical",
        "gi bleeding,internal bleeding,stomach bleeding requiring transfusions",
        "SSA Blue Book 5.02",
    ),
    (
        "Chronic liver disease (CLD)",
        "physical",
        "liver disease,cirrhosis,hepatitis-related liver damage",
        "SSA Blue Book 5.05",
    ),
    (
        "Inflammatory bowel disease (IBD)",
        "physical",
        "crohn's disease,ulcerative colitis,ibd",
        "SSA Blue Book 5.06",
    ),
    (
        "Weight loss due to any digestive disorder",
        "physical",
        "malnutrition,severe weight loss,digestive wasting",
        "SSA Blue Book 5.08",
    ),
    (
        "Intestinal failure",
        "physical",
        "short bowel syndrome,needs iv nutrition,total parenteral nutrition",
        "SSA Blue Book 105.07 (Childhood Listings, Part B)",
    ),
    (
        "Need for supplemental daily enteral feeding via feeding tube",
        "physical",
        "feeding tube,g-tube fed baby,tube feeding,gastrostomy",
        "SSA Blue Book 105.10 (Childhood Listings, Part B)",
    ),
    # --- 6.00 Genitourinary Disorders --------------------------------------
    (
        "Chronic kidney disease, with kidney transplant",
        "physical",
        "kidney transplant,post-transplant kidney recovery",
        "SSA Blue Book 6.04",
    ),
    (
        "Chronic kidney disease, with impairment of kidney function",
        "physical",
        "chronic kidney disease,ckd,kidney failure,renal disease,esrd,"
        "end-stage renal disease,dialysis",
        "SSA Blue Book 6.05; Medicare special enrollment rule for ESRD",
    ),
    (
        "Nephrotic syndrome",
        "physical",
        "nephrotic syndrome,protein in urine kidney disorder",
        "SSA Blue Book 6.06",
    ),
    (
        "Complications of chronic kidney disease",
        "physical",
        "dialysis complications,kidney disease complications,esrd "
        "complications",
        "SSA Blue Book 6.09",
    ),
    (
        "Congenital genitourinary disorder",
        "physical",
        "born with bladder or urinary defect,congenital urinary tract "
        "problem,prune belly syndrome",
        "SSA Blue Book 106.07 (Childhood Listings, Part B)",
    ),
    # --- 7.00 Hematological Disorders --------------------------------------
    (
        "Hemolytic anemias, including sickle cell disease and thalassemia",
        "physical",
        "sickle cell disease,thalassemia,hemolytic anemia",
        "SSA Blue Book 7.05",
    ),
    (
        "Disorders of thrombosis and hemostasis",
        "physical",
        "blood clotting disorder,hemophilia,excessive bleeding "
        "disorder,von willebrand disease",
        "SSA Blue Book 7.08",
    ),
    (
        "Disorders of bone marrow failure",
        "physical",
        "bone marrow failure,aplastic anemia,myelodysplastic syndrome",
        "SSA Blue Book 7.10",
    ),
    (
        "Hematological disorders treated by bone marrow or stem cell "
        "transplantation",
        "physical",
        "bone marrow transplant,stem cell transplant recovery",
        "SSA Blue Book 7.17",
    ),
    (
        "Repeated complications of hematological disorders",
        "physical",
        "recurring blood disorder complications,chronic blood disease "
        "flare-ups",
        "SSA Blue Book 7.18",
    ),
    # --- 8.00 Skin Disorders ------------------------------------------------
    (
        "Genetic photosensitivity disorders",
        "physical",
        "sun sensitivity disorder,xeroderma pigmentosum,porphyria",
        "SSA Blue Book 8.07",
    ),
    (
        "Burns",
        "physical",
        "severe burns,burn injury,burn scarring",
        "SSA Blue Book 8.08",
    ),
    (
        "Chronic conditions of the skin or mucous membranes",
        "physical",
        "chronic skin disease,psoriasis,severe eczema,skin ulcers,ichthyosis",
        "SSA Blue Book 8.09",
    ),
    # --- 9.00 Endocrine Disorders -------------------------------------------
    # SSA has no standalone endocrine listings; diabetes and other
    # endocrine conditions are evaluated under the body system they
    # affect (e.g. diabetic neuropathy under 11.00, diabetic
    # retinopathy under 2.00).
    (
        "Diabetes mellitus with complications",
        "physical",
        "diabetes,diabetic neuropathy,diabetic retinopathy,type 1 "
        "diabetes,type 2 diabetes",
        "SSA Blue Book 9.00 (evaluated under the body system affected)",
    ),
    (
        "Diabetes mellitus in a child under age 6 requiring daily insulin",
        "physical",
        "type 1 diabetes toddler,insulin-dependent diabetes under 6,"
        "juvenile diabetes infant",
        "SSA Blue Book 109.08 (Childhood Listings, Part B)",
    ),
    # --- 10.00 Congenital Disorders that Affect Multiple Body Systems ------
    (
        "Non-mosaic Down syndrome",
        "physical",
        "down syndrome,trisomy 21",
        "SSA Blue Book 10.06",
    ),
    (
        "A catastrophic congenital disorder",
        "physical",
        "anencephaly,trisomy 13,patau syndrome,trisomy 18,edwards "
        "syndrome,cri du chat,infantile tay-sachs",
        "SSA Blue Book 110.08 (Childhood Listings, Part B)",
    ),
    (
        "Low birth weight in infants",
        "physical",
        "low birth weight,premature infant weight,tiny baby,nicu baby",
        "SSA Blue Book 100.04 (Childhood Listings, Part B)",
    ),
    (
        "Failure to thrive in children",
        "physical",
        "failure to thrive,ftt,not gaining weight,growth failure baby,"
        "poor weight gain toddler",
        "SSA Blue Book 100.05 (Childhood Listings, Part B)",
    ),
    # --- 11.00 Neurological Disorders ----------------------------------------
    (
        "Epilepsy",
        "physical",
        "epilepsy,seizures,seizure disorder",
        "SSA Blue Book 11.02",
    ),
    (
        "Vascular insult to the brain",
        "physical",
        "stroke,brain hemorrhage,cerebrovascular accident,cva",
        "SSA Blue Book 11.04",
    ),
    (
        "Benign brain tumors",
        "physical",
        "brain tumor,benign tumor of the brain",
        "SSA Blue Book 11.05",
    ),
    (
        "Parkinsonian syndrome",
        "physical",
        "parkinson's disease,parkinsonism,tremor disorder",
        "SSA Blue Book 11.06",
    ),
    (
        "Cerebral palsy",
        "physical",
        "cerebral palsy,cp",
        "SSA Blue Book 11.07",
    ),
    (
        "Spinal cord disorders",
        "physical",
        "spinal cord injury,paralysis,spinal cord damage,paraplegia,"
        "quadriplegia",
        "SSA Blue Book 11.08",
    ),
    (
        "Multiple sclerosis",
        "physical",
        "multiple sclerosis,ms",
        "SSA Blue Book 11.09",
    ),
    (
        "Amyotrophic lateral sclerosis (ALS)",
        "physical",
        "als,lou gehrig's disease",
        "SSA Blue Book 11.10; Medicare special enrollment rule for ALS",
    ),
    (
        "Post-polio syndrome",
        "physical",
        "post-polio syndrome,polio after-effects",
        "SSA Blue Book 11.11",
    ),
    (
        "Myasthenia gravis",
        "physical",
        "myasthenia gravis,muscle weakness disorder",
        "SSA Blue Book 11.12",
    ),
    (
        "Muscular dystrophy",
        "physical",
        "muscular dystrophy,md,duchenne md",
        "SSA Blue Book 11.13",
    ),
    (
        "Peripheral neuropathy",
        "physical",
        "neuropathy,nerve damage,numbness in hands and feet",
        "SSA Blue Book 11.14",
    ),
    (
        "Neurodegenerative disorders of the central nervous system",
        "physical",
        "huntington's disease,friedreich's ataxia,neurodegenerative "
        "disease,spinocerebellar degeneration",
        "SSA Blue Book 11.17",
    ),
    (
        "Traumatic brain injury",
        "physical",
        "tbi,head injury,brain injury",
        "SSA Blue Book 11.18",
    ),
    (
        "Coma or persistent vegetative state",
        "physical",
        "coma,vegetative state,unresponsive",
        "SSA Blue Book 11.20",
    ),
    (
        "Motor neuron disorders other than ALS",
        "physical",
        "motor neuron disease,progressive muscle weakness disorder,"
        "spinal muscular atrophy",
        "SSA Blue Book 11.22",
    ),
    (
        "Communication impairment",
        "physical",
        "severe speech delay,nonverbal child,language disorder from "
        "brain injury",
        "SSA Blue Book 111.09 (Childhood Listings, Part B)",
    ),
    # --- 12.00 Mental Disorders -----------------------------------------------
    (
        "Neurocognitive disorders",
        "mental_health",
        "dementia,alzheimer's,memory loss,cognitive decline",
        "SSA Blue Book 12.02",
    ),
    (
        "Schizophrenia spectrum and other psychotic disorders",
        "mental_health",
        "schizophrenia,schizoaffective disorder,psychosis,hallucinations,"
        "delusions",
        "SSA Blue Book 12.03",
    ),
    (
        "Depressive, bipolar and related disorders",
        "mental_health",
        "depression,major depressive disorder,mdd,bipolar disorder,"
        "manic depression,disruptive mood dysregulation disorder",
        "SSA Blue Book 12.04",
    ),
    (
        "Intellectual disorder",
        "mental_health",
        "intellectual disability,developmental disability,low iq",
        "SSA Blue Book 12.05",
    ),
    (
        "Anxiety and obsessive-compulsive disorders",
        "mental_health",
        "anxiety,gad,generalized anxiety disorder,panic disorder,social "
        "anxiety,ocd,obsessive-compulsive disorder,separation anxiety",
        "SSA Blue Book 12.06",
    ),
    (
        "Somatic symptom and related disorders",
        "mental_health",
        "somatic symptom disorder,chronic unexplained pain,conversion disorder",
        "SSA Blue Book 12.07",
    ),
    (
        "Personality and impulse-control disorders",
        "mental_health",
        "personality disorder,borderline personality disorder,bpd,"
        "impulse control disorder",
        "SSA Blue Book 12.08",
    ),
    (
        "Autism spectrum disorder",
        "mental_health",
        "autism,asd,asperger's",
        "SSA Blue Book 12.10",
    ),
    (
        "Neurodevelopmental disorders",
        "mental_health",
        "adhd,attention deficit hyperactivity disorder,attention-"
        "deficit,learning disability,developmental delay,tourette's",
        "SSA Blue Book 12.11",
    ),
    (
        "Eating disorders",
        "mental_health",
        "anorexia,bulimia,binge eating disorder",
        "SSA Blue Book 12.13",
    ),
    (
        "Trauma- and stressor-related disorders",
        "mental_health",
        "ptsd,post-traumatic stress disorder,post traumatic stress,"
        "trauma disorder,reactive attachment disorder",
        "SSA Blue Book 12.15",
    ),
    (
        "Developmental disorders in infants and toddlers",
        "mental_health",
        "global developmental delay,toddler not hitting milestones,"
        "regression in skills",
        "SSA Blue Book 112.14 (Childhood Listings, Part B)",
    ),
    # --- 13.00 Cancer (Malignant Neoplastic Diseases) ----------------------
    (
        "Soft tissue cancers of the head and neck",
        "physical",
        "head and neck cancer,throat cancer",
        "SSA Blue Book 13.02",
    ),
    (
        "Skin cancer",
        "physical",
        "skin cancer",
        "SSA Blue Book 13.03",
    ),
    (
        "Soft tissue sarcoma",
        "physical",
        "soft tissue sarcoma,sarcoma",
        "SSA Blue Book 13.04",
    ),
    (
        "Lymphoma",
        "physical",
        "lymphoma,hodgkin's lymphoma,non-hodgkin lymphoma",
        "SSA Blue Book 13.05",
    ),
    (
        "Leukemia",
        "physical",
        "leukemia,blood cancer",
        "SSA Blue Book 13.06",
    ),
    (
        "Multiple myeloma",
        "physical",
        "multiple myeloma,bone marrow cancer",
        "SSA Blue Book 13.07",
    ),
    (
        "Salivary gland cancer",
        "physical",
        "salivary gland cancer",
        "SSA Blue Book 13.08",
    ),
    (
        "Thyroid gland cancer",
        "physical",
        "thyroid cancer",
        "SSA Blue Book 13.09",
    ),
    (
        "Breast cancer",
        "physical",
        "breast cancer",
        "SSA Blue Book 13.10",
    ),
    (
        "Skeletal system sarcoma",
        "physical",
        "bone cancer,skeletal sarcoma",
        "SSA Blue Book 13.11",
    ),
    (
        "Cancer of the maxilla, orbit or temporal fossa",
        "physical",
        "facial bone cancer,jaw or eye socket cancer",
        "SSA Blue Book 13.12",
    ),
    (
        "Cancer of the nervous system",
        "physical",
        "brain cancer,spinal cord cancer,nervous system cancer",
        "SSA Blue Book 13.13",
    ),
    (
        "Lung cancer",
        "physical",
        "lung cancer",
        "SSA Blue Book 13.14",
    ),
    (
        "Cancer of the pleura or mediastinum",
        "physical",
        "mesothelioma,chest cavity cancer",
        "SSA Blue Book 13.15",
    ),
    (
        "Cancer of the esophagus or stomach",
        "physical",
        "esophageal cancer,stomach cancer",
        "SSA Blue Book 13.16",
    ),
    (
        "Small intestine cancer",
        "physical",
        "small intestine cancer",
        "SSA Blue Book 13.17",
    ),
    (
        "Large intestine cancer",
        "physical",
        "colon cancer,colorectal cancer",
        "SSA Blue Book 13.18",
    ),
    (
        "Cancer of the liver or gallbladder",
        "physical",
        "liver cancer,gallbladder cancer",
        "SSA Blue Book 13.19",
    ),
    (
        "Pancreatic cancer",
        "physical",
        "pancreatic cancer",
        "SSA Blue Book 13.20",
    ),
    (
        "Cancer of the kidneys, adrenal glands, or ureters",
        "physical",
        "kidney cancer,adrenal gland cancer",
        "SSA Blue Book 13.21",
    ),
    (
        "Urinary bladder cancer",
        "physical",
        "bladder cancer",
        "SSA Blue Book 13.22",
    ),
    (
        "Cancers of the female genital tract",
        "physical",
        "ovarian cancer,cervical cancer,uterine cancer",
        "SSA Blue Book 13.23",
    ),
    (
        "Prostate gland cancer",
        "physical",
        "prostate cancer",
        "SSA Blue Book 13.24",
    ),
    (
        "Testicular cancer",
        "physical",
        "testicular cancer",
        "SSA Blue Book 13.25",
    ),
    (
        "Penile cancer",
        "physical",
        "penile cancer",
        "SSA Blue Book 13.26",
    ),
    (
        "Cancer, primary site unknown",
        "physical",
        "cancer of unknown origin,unknown primary cancer",
        "SSA Blue Book 13.27",
    ),
    (
        "Cancer treated by bone marrow or stem cell transplantation",
        "physical",
        "cancer with bone marrow transplant,stem cell transplant for cancer",
        "SSA Blue Book 13.28",
    ),
    (
        "Malignant melanoma",
        "physical",
        "melanoma,skin cancer melanoma",
        "SSA Blue Book 13.29",
    ),
    (
        "Malignant solid tumors in children",
        "physical",
        "childhood cancer tumor,pediatric solid tumor cancer",
        "SSA Blue Book 113.03 (Childhood Listings, Part B)",
    ),
    (
        "Retinoblastoma",
        "physical",
        "retinoblastoma,eye cancer in a child",
        "SSA Blue Book 113.12 (Childhood Listings, Part B)",
    ),
    (
        "Neuroblastoma",
        "physical",
        "neuroblastoma",
        "SSA Blue Book 113.21 (Childhood Listings, Part B)",
    ),
    # --- 14.00 Immune System Disorders -------------------------------------
    (
        "Systemic lupus erythematosus",
        "physical",
        "lupus,sle",
        "SSA Blue Book 14.02",
    ),
    (
        "Systemic vasculitis",
        "physical",
        "vasculitis,blood vessel inflammation",
        "SSA Blue Book 14.03",
    ),
    (
        "Systemic sclerosis (scleroderma)",
        "physical",
        "scleroderma,systemic sclerosis",
        "SSA Blue Book 14.04",
    ),
    (
        "Polymyositis and dermatomyositis",
        "physical",
        "polymyositis,dermatomyositis,juvenile dermatomyositis,muscle "
        "inflammation disease",
        "SSA Blue Book 14.05",
    ),
    (
        "Undifferentiated and mixed connective tissue disease",
        "physical",
        "mixed connective tissue disease,autoimmune connective tissue disorder",
        "SSA Blue Book 14.06",
    ),
    (
        "Immune deficiency disorders, excluding HIV infection",
        "physical",
        "immune deficiency,primary immunodeficiency,weakened immune "
        "system,scid",
        "SSA Blue Book 14.07",
    ),
    (
        "Inflammatory arthritis",
        "physical",
        "rheumatoid arthritis,ra,inflammatory arthritis,juvenile "
        "idiopathic arthritis,jia,juvenile rheumatoid arthritis",
        "SSA Blue Book 14.09",
    ),
    (
        "Sjögren's syndrome",
        "physical",
        "sjogren's syndrome,dry eyes and mouth autoimmune disease",
        "SSA Blue Book 14.10",
    ),
    (
        "Human immunodeficiency virus (HIV) infection",
        "physical",
        "hiv,aids,hiv infection",
        "SSA Blue Book 14.11",
    ),
]
