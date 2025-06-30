import streamlit as st
import pandas as pd
import asyncio
import duckdb
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import streamlit_nested_layout

#TO-DO: integrate video

#TO-DO: make it work with no prior recorded workout
#TO-DO handle multi users/profil to get sessions?
#TO-DO: Make Note its own field in gsheet
#TO-DO avoid global variable

from streamlit_browser_storage import LocalStorage

s = LocalStorage(key="exercise_data")

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
    #st.write(s.get_all())
    st.write(st.session_state)
def createClick():
    s.set("some_key", "test: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.write(s.get("some_key"))
    st.write(s.get_all())

if st.session_state.showDataClicked:
    showDataToSend()

#st.button("Create Data", on_click=createClick, key="createData")
#st.button("Show Data", on_click=showDataClick, key="showData")
#st.button("Hide Data", on_click=hideDataClick, key="hideData")
#st.button("Clear Data", on_click=clearDataClick, key="clearData")

if 'workoutSessionClicked' not in st.session_state:
    st.session_state.workoutSessionClicked = False

if 'createWorkoutclicked' not in st.session_state:
    st.session_state.createWorkoutclicked = False

if 'resumeWorkoutclicked' not in st.session_state:
    st.session_state.resumeWorkoutclicked=False

def getDataTemplate():
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
        "Sets Completion": [],
        "Completed": [],
        "Date":[],
        "Rep": [],
        "Dones":[],
    }

def setDFFromGoogleData(dataframe):
    lastWorkOutRecord = dataframe[-1:]#duckdb.query("SELECT Date, Session FROM dataframe").to_df().tail(1) #issue being when there is 2 sessions on the same day, it gets order wrongly
    lastWorkOutDate =  lastWorkOutRecord["Date"].iloc[0]
    lastWorkoutSession =  lastWorkOutRecord["Session"].iloc[0]
    
    query = "SELECT Count(Completed) as NbrUncompleted, Max(Date) as Date, Max(Session) as Session FROM dataframe WHERE Completed = " + str(False) + " AND Date ='" + str(lastWorkOutDate) +"'"
    #st.write(duckdb.query(query).to_df())

    infoUncompletedSet = duckdb.query(query).to_df()
    
    nbrUncompletedSets = infoUncompletedSet.count()["NbrUncompleted"]
    #st.write(infoUncompletedSet)
    completedSet = duckdb.query("SELECT * FROM dataframe WHERE NOT (Session = '" + str(infoUncompletedSet["Session"][0]) + "' AND Date = '" + str(infoUncompletedSet["Date"][0]) + "')").to_df()

    uncompletedSet = {}
    if nbrUncompletedSets > 0:
        uncompletedSet = duckdb.query(f"SELECT * FROM dataframe WHERE Session = '{lastWorkoutSession}' AND Date = '" + str(infoUncompletedSet["Date"][0]) + "'").to_df()
    return {"allData": dataframe, "completedSet": completedSet, "uncompletedSet": uncompletedSet, "lastWorkoutSession": lastWorkoutSession, "lastWorkOutDate": lastWorkOutDate}


def getGoogleSheetData():
    queryString="Select * FROM Raph WHERE Session IS NOT NULL"
    myConn = conn.query(queryString)
    return pd.DataFrame(myConn)

existingData = setDFFromGoogleData(getGoogleSheetData()) #{"allData": dataframe, "completedSet": completedSet, "uncompletedSet": uncompletedSet}

def fixGoogleFormulainAllDataSet(dataToSend,allDataSet):
    st.write(dataToSend)
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
        initTotalLbs.append(f"=SUM(O{i+2}:Q{i+2})*E{i+2}")
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

def resumeWorkoutclick_button():
    st.session_state.title = "Resume Workout"
    st.session_state.resumeWorkoutclicked = True

def updateDataToSend(data):
    exercice = data.get("Exercise")
    lbs = data.get("Lbs")
    nbrExercise = len(exercice)

    data["Sets x Reps"] = [None] * nbrExercise
    data["Equipment"] = [None] * nbrExercise
    data["Total Lbs"] = [None] * nbrExercise
    data["Primary Muscles"] = [None] * nbrExercise
    data["Secondary Muscles"] = [None] * nbrExercise
    data["Completed"] = []
    for i in range(len(exercice)):
        compactExcerciseName = exercice[i].replace(" ", "")
        note = st.session_state.get(f"input{compactExcerciseName}")
        edited_rows=st.session_state.get(f"data_editor{compactExcerciseName}").get("edited_rows")

        lbsExercise = lbs[i]
        reps = (data.get("Rep")[i]).split(",")
        dones = (data.get("Dones")[i]).split(",")
        setsCompletion=[]

        if edited_rows != {}:
            for j in range(len(reps)):
                if edited_rows.get(j) is not None:
                    if edited_rows.get(j).get("Rep") is not None:
                        reps[j] = edited_rows.get(j).get("Rep")
                    if edited_rows.get(j).get("Weight") is not None:
                        data.get("Lbs")[i] = edited_rows.get(j).get("Weight")
                    if edited_rows.get(j).get("Done") is not None:
                        #st.write("edited_rows.get(j).get('Done'): " + compactExcerciseName + " : row:" + str(j))
                        #st.write(edited_rows.get(j).get('Done'))
                        
                        dones[j] = edited_rows.get(j).get("Done")>0
        
        completed = True
        for j in range(len(dones)):
            completed = completed and (dones[j]==True or dones[j]=="True")
            setsCompletion.append(str(int((dones[j]==True or dones[j]=="True")>0)))

        if note != None:
            reps.append(note)
        note = (",").join(reps)
        data.get("Completed").append(completed)
        data.get("Sets Completion").append(",".join(setsCompletion))
        data.get("Notes").append(note)
    
    del data["Rep"]
    del data["Dones"]
    return data

def click_Submitbutton(exerciseDataFromForm):
    #to-do: if workout completed, true else false
    st.session_state.createWorkoutclicked = True

    st.session_state.title = "Gym Tracker"
    dataToSend = updateDataToSend(exerciseDataFromForm)
    dataToSend = fixGoogleFormulainAllDataSet(dataToSend, existingData.get("completedSet"))
    #s.set("lastSubmittedData", "dataToSend")
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet="Raph",data=(pd.DataFrame(dataToSend)))
    #initAll()
    st.session_state.createWorkoutclicked = False
    st.session_state.resumeWorkoutclicked=False

    st.cache_data.clear()
    st.success("Workout data submitted successfully!")

def buildForm(exerciseData, resumed=False):
    
    dataToSend = getDataTemplate()
    session=exerciseData.get('Session', 0).iloc[0]
    with st.form("my_form"):
        if resumed:
            previousWorkOutData = getLastWorkout(session, existingData.get('lastWorkOutDate'))
            #st.write(exerciseData.get('lastWorkOutDate'))
            #st.write(previousWorkOutData)
        for i in range(len(exerciseData.get("Exercise", 0))):
                with st.container():
                    
                    excerciseName=exerciseData.get('Exercise', 0).iloc[i]
                    compactExcerciseName = excerciseName.replace(" ", "")
                    #with st.form(compactExcerciseName):

                    aNotes=exerciseData.get('Notes', 0).iloc[i].split(",")
                    noteValue = None
                    aDone = exerciseData.get('Sets Completion')[i].split(",")
                    if resumed:
                        if exerciseData.get('Completed', 0).iloc[i]>0:
                            expanded = False
                        else:
                            expanded = True
                        if len(aNotes) == 4:
                            noteValue = aNotes[3]
                    else:
                        done = False
                        expanded = True
                    setsxReps=exerciseData.get("Sets x Reps", 0).iloc[i]
                    asetsxReps = setsxReps.split(" x ")
                    nbrSets=int(asetsxReps[0])

                    with st.expander(excerciseName, expanded=expanded):
                            col1, col2 = st.columns(2)
                            col1.subheader(f"{excerciseName}: {setsxReps}")   
                            weight = exerciseData.get('Lbs', 0).iloc[i]
                            aDF = []
                            for j in range(nbrSets):
                                if resumed:
                                    done = int(aDone[j])>0
                                else:
                                    done=False
                                aDF.append(dict(Weight=weight,
                                    Rep=aNotes[j],
                                    Done = done,
                                    )
                                )
                            
                            editedDF=col1.data_editor(pd.DataFrame(aDF),key=f"data_editor{compactExcerciseName}", hide_index=True, num_rows="fixed")
                            with col2.expander("Last Session Info", expanded=True):
                                if resumed:
                                    aNotes = previousWorkOutData.get('Notes', 0).iloc[i].split(",")
                                    if len(aNotes) > nbrSets:
                                        st.write(f"Notes: {aNotes[3]}")
                                else:
                                    if len(aNotes) > nbrSets:
                                        st.write(f"Notes: {aNotes[3]}")                                
                                st.write(f"Lbs: {weight}")
                                st.write(f"Total Lbs: {exerciseData.get('Total Lbs', 0).iloc[i]}")
                            with col2.expander("Description", expanded=False):
                                st.write(f"Equipment: {exerciseData.get('Equipment', 0).iloc[i]}")
                                st.write(f"Primary Muscles: {exerciseData.get('Primary Muscles', 0).iloc[i]}")
                                st.write(f"Secondary Muscles: {exerciseData.get('Secondary Muscles', 0).iloc[i]}")
                            #with col2.expander("Video", expanded=False):
                            #    st.video("https://app.fitnessai.com/exercises/00431201-Barbell-Full-Squat-Thighs.mp4",autoplay=False, loop=True)
                            text_input=col1.text_input(label="Notes", value=noteValue, key=f"input{compactExcerciseName}", placeholder="Enter Notes")
                            reps=editedDF.loc[0]["Rep"]+","+editedDF.loc[1]["Rep"]+","+editedDF.loc[2]["Rep"]
                            dones=str(editedDF.loc[0]["Done"])+","+str(editedDF.loc[1]["Done"])+","+str(editedDF.loc[2]["Done"])
                            dataToSend.get("Session").append(session)
                            dataToSend.get("Exercise").append(excerciseName)
                            dataToSend.get("Lbs").append(weight)
                            dataToSend.get("Rep").append(reps)
                            dataToSend.get("Dones").append(dones)
                            dataToSend.get("Completed").append(done)
                            dataToSend.get("Date").append(datetime.today().strftime('%Y/%m/%d'))
                        #col2.form_submit_button('Submit', on_click=click_Submitbutton, args=[dataToSend])
    #return dataToSend
    
        st.form_submit_button('Submit', on_click=click_Submitbutton, args=[dataToSend])


def getLastWorkout(session, LastWorkoutDate = None):
    #initAll()
    #existingData = {completedSet": completedSet, "uncompletedSet": uncompletedSet}
    allData = existingData["allData"]
    if LastWorkoutDate!=None:
        queryString=f"Select Max(Date) as LastDate, Count(Date) as NbrExercise FROM allData WHERE Session='{session}' AND Date!='{LastWorkoutDate}' Group By Date ORDER BY LastDate Desc;"
    else:
        queryString=f"Select Max(Date) as LastDate, Count(Date) as NbrExercise FROM allData WHERE Session='{session}' Group By Date ORDER BY LastDate Desc;"
    lastWorkoutDate = duckdb.query(queryString).to_df()["LastDate"][0]
    if session is not None:
        queryString=f"Select * FROM allData WHERE Session='{session}' AND Date='{lastWorkoutDate}';"
        exerciseData = duckdb.query(queryString).to_df()
    return exerciseData
        



if 'title' not in st.session_state:
    st.session_state.title = "Gym Tracker"
st.title(st.session_state.title)

if st.session_state.createWorkoutclicked==False:
    createWorkOut = st.button("Create Workout", on_click=createWorkoutclick_button, key="createWorkout")
#    selection = None

#existingData = setDFFromGoogleData(getGoogleSheetData()) #{completedSet": completedSet, "uncompletedSet": uncompletedSet}

if st.session_state.resumeWorkoutclicked==False and len(existingData["uncompletedSet"]) != 0:
    resumeWorkOut = st.button("Resume Workout", on_click=resumeWorkoutclick_button, key="resumeWorkout")

if st.session_state.resumeWorkoutclicked==True:
    exerciseData = existingData["uncompletedSet"]
    st.write(exerciseData)
    buildForm(exerciseData, True)
    

if st.session_state.createWorkoutclicked:
    options = ["A", "B"]
    
    defaultOption = options[(options.index(existingData["lastWorkoutSession"])+1)%len(options)]

    selection = st.pills("Workout", options, default = defaultOption, selection_mode="single")
    #existingData: {"allData": dataframe, "completedSet": completedSet, "uncompletedSet": uncompletedSet}
    if selection is not None:
        exerciseData = getLastWorkout(selection)
        buildForm(exerciseData)

