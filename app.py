import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_browser_storage import LocalStorage

s = LocalStorage(key="exercise_data")

#st.write(s.expires_in("some_key"))
#st.write(s.exists("some_key"))
#st.write(s.delete("some_key"))


st.set_page_config(page_title="Gym Tracker", page_icon=":mechanical_arm:", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

if 'showDataClicked' not in st.session_state:
    st.session_state.showDataClicked = False
def showDataClick():
    st.session_state.showDataClicked = True

def hideDataClick():
    st.session_state.showDataClicked = False

def clearDataClick():
    s.delete("some_key")

def showDataToSend():
    st.write(s.get_all())
    st.write(st.session_state)
def createClick():
    s.set("some_key", "test: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.write(s.get("some_key"))
    st.write(s.get_all())

if st.session_state.showDataClicked:
    showDataToSend()

st.button("Create Data", on_click=createClick, key="createData")
st.button("Show Data", on_click=showDataClick, key="showData")
st.button("Hide Data", on_click=hideDataClick, key="hideData")
st.button("Clear Data", on_click=clearDataClick, key="clearData")


if 'workoutSessionClicked' not in st.session_state:
    st.session_state.workoutSessionClicked = False
if 'createWorkoutclicked' not in st.session_state:
    st.session_state.createWorkoutclicked = False

#unused to delete after refactoring done
def initDataToSend():
    return {
        "Session": [],
        "Exercise": [],
        "Sets x Reps": [],
        "Equipment": [],
        "Lbs": [],
        "Notes": [],
        "Total Lbs": [],
        "Primary Muscles": [],
        "Secondary Muscles": [],
        "Date":[],
        "Rep": [],
    }
#if 'dataToSend' not in st.session_state:
#    initDataToSend()

def initDataSet():
    queryString="Select * FROM Raph WHERE Session IS NOT NULL"
    return  conn.query(queryString)
#if 'allDataSet' not in st.session_state:
#    initDataSet()

def initAll():
    #initDataToSend()
    initDataSet()

def fixGoogleFormulainAllDataSet(dataToSend,allDataSet):

    dataToSend = pd.concat([pd.DataFrame(allDataSet), pd.DataFrame(dataToSend)], ignore_index=True)
    setSize = len(dataToSend.get("Sets x Reps"))
    initSetxReps = []
    initEquip =[]
    initPrimaryMuscles = []
    initSecondaryMuscles = []
    initTotalLbs = []
    initSplit = []
    initSplit2 = [None]*setSize
    initSplit3 = [None]*setSize
    initSplit4 = [None]*setSize
    for i in range(setSize):
        initSetxReps.append(f"=VLOOKUP(B{i+2},Exercise!A:C,3,False)")
        initEquip.append(f"=VLOOKUP(B{i+2},Exercise!A:B,2,False)")
        initTotalLbs.append(f"=SUM(L{i+2}:N{i+2})*E{i+2}")
        initPrimaryMuscles.append(f"=VLOOKUP(B{i+2},Exercise!A:E,4,False)")
        initSecondaryMuscles.append(f"=VLOOKUP(B{i+2},Exercise!A:E,5,False)")
        initSplit.append(f"=IF(LEFT(F{i+2},8)<>\"Previous\", SPLIT(F{i+2}, \",\"))")
    dataToSend["Sets x Reps"] = initSetxReps
    dataToSend["Equipment"] = initEquip
    dataToSend["Total Lbs"] = initTotalLbs
    dataToSend["Primary Muscles"] = initPrimaryMuscles
    dataToSend["Secondary Muscles"] = initSecondaryMuscles
    dataToSend["Split"] = initSplit
    dataToSend["Split2"] = initSplit2
    dataToSend["Split3"] = initSplit3
    dataToSend["Split4"] = initSplit4

    return dataToSend


def click_button():
    st.session_state.workoutSessionClicked = True

def createWorkoutclick_button():
    st.session_state.title = "Create Workout"
    st.session_state.createWorkoutclicked = True

def updateDataToSend(data):
    exercice = data.get("Exercise")
    lbs = data.get("Lbs")
    nbrExercise = len(exercice)

    data["Sets x Reps"] = [None] * nbrExercise
    data["Equipment"] = [None] * nbrExercise
    data["Total Lbs"] = [None] * nbrExercise
    data["Primary Muscles"] = [None] * nbrExercise
    data["Secondary Muscles"] = [None] * nbrExercise
    st.write("Updating data to send...")
    st.write(data)
    for i in range(len(exercice)):
        compactExcerciseName = exercice[i].replace(" ", "")
        note = st.session_state.get(f"input{compactExcerciseName}")
        edited_rows=st.session_state.get(f"data_editor{compactExcerciseName}").get("edited_rows")

        lbsExercise = lbs[i]
        reps = (data.get("Rep")[i]).split(",")
        
        if edited_rows != {}:
            for j in range(len(reps)):
                if edited_rows.get(j) is not None:
                    if edited_rows.get(j).get("Rep") is not None:
                        reps[j] = edited_rows.get(j).get("Rep")
                    if edited_rows.get(j).get("Weight") is not None:
                        data.get("Lbs")[i] = edited_rows.get(j).get("Weight")
        if note != "":
            reps.append(note)
        note = ",".join(reps)

        data.get("Notes").append(note)
    
    del data["Rep"]
    return data

def click_Submitbutton(dataToSend):
    st.session_state.createWorkoutclicked = False
    st.session_state.title = "Gym Tracker"
    dataToSend = updateDataToSend(dataToSend)
    st.dataframe(pd.DataFrame(dataToSend))

    allDataSet = initDataSet()

    dataToSend = fixGoogleFormulainAllDataSet(dataToSend, allDataSet)
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet="Raph",data=(pd.DataFrame(dataToSend)))
    initAll()

    st.cache_data.clear()
    st.success("Workout data submitted successfully!")

def buildForm(exerciseData):
    dataToSend = initDataToSend()
    session=exerciseData.get('Session', 0).iloc[0]
    for i in range(len(exerciseData.get("Exercise", 0))):
            with st.container():
                
                excerciseName=exerciseData.get('Exercise', 0).iloc[i]
                
                with st.expander(excerciseName, expanded=True):
                    col1, col2 = st.columns(2)
                    compactExcerciseName = excerciseName.replace(" ", "")
                    setsxReps=exerciseData.get("Sets x Reps", 0).iloc[i]
                    asetsxReps = setsxReps.split(" x ")

                    col1.subheader(f"{excerciseName}: {setsxReps}")   
                    col2.write(f"Equipment: {exerciseData.get('Equipment', 0).iloc[i]}")
                    
                    col2.write(f"Primary Muscles: {exerciseData.get('Primary Muscles', 0).iloc[i]}")
                    col2.write(f"Secondary Muscles: {exerciseData.get('Secondary Muscles', 0).iloc[i]}")
                    col2.write(f"Total Lbs: {exerciseData.get('Total Lbs', 0).iloc[i]}")
                    weight = exerciseData.get('Lbs', 0).iloc[i]
                    col1.write(f"Lbs: {weight}")

                    aNotes=exerciseData.get('Notes', 0).iloc[i].split(",")
                    
                    aDF = []
                    if len(asetsxReps)==2:
                        for j in range(int(asetsxReps[0])):
                            aDF.append(dict(Weight=weight,
                                Rep=aNotes[j],
                                Done = False,
                                )
                            )
                    
                    editedDF=col1.data_editor(pd.DataFrame(aDF),key=f"data_editor{compactExcerciseName}", hide_index=True, num_rows="fixed")
                    

                    if len(aNotes) > int(asetsxReps[0]):
                        col2.write(f"Previous Notes: {aNotes[3]}")
                    text_input=col1.text_input(label="Notes", key=f"input{compactExcerciseName}", placeholder="Enter Notes")
                    reps=editedDF.loc[0]["Rep"]+","+editedDF.loc[1]["Rep"]+","+editedDF.loc[2]["Rep"]
                    dataToSend.get("Session").append(session)
                    dataToSend.get("Exercise").append(excerciseName)
                    dataToSend.get("Lbs").append(weight)
                    dataToSend.get("Rep").append(reps)
                    dataToSend.get("Date").append(datetime.today().strftime('%Y/%m/%d'))
    return dataToSend


def getLastWorkout(session):
    if session is not None:
        initAll()
        queryString=f"Select Max(Date) as LastDate, Count(Date) as NbrExercise FROM Raph WHERE Session='{session}' Group By Date;"

        lastWorkoutDate = conn.query(queryString).sort_values(by="LastDate", ascending=False).get("LastDate", 0).iloc[0]
        #queryString=f"Select Exercise, 'Sets x Reps', Equipment, Lbs, Notes, 'Total Lbs', 'Primary Muscles', 'Secondary Muscles', Date FROM Raph WHERE Session='{session}' AND Date='{lastWorkoutDate}';"
        queryString=f"Select * FROM Raph WHERE Session='{session}' AND Date='{lastWorkoutDate}';"
        
        exerciseData = conn.query(queryString)
        return exerciseData
        

if 'title' not in st.session_state:
    st.session_state.title = "Gym Tracker"
st.title(st.session_state.title)

if st.session_state.createWorkoutclicked==False:
    createWorkOut = st.button("Create Workout", on_click=createWorkoutclick_button, key="createWorkout")
#    selection = None

if st.session_state.createWorkoutclicked:
    options = ["A", "B"]
    selection = st.pills("Workout", options, selection_mode="single")
    if selection is not None:
        initAll()
        with st.form("my_form"):
            exerciseData = getLastWorkout(selection)
            dataToSend = buildForm(exerciseData)
            st.form_submit_button('Submit', on_click=click_Submitbutton, args=[dataToSend])



