import streamlit as st
import pandas as pd
import asyncio
import duckdb
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import streamlit_nested_layout
import numpy as np
from abc import ABC, abstractmethod
import json


#TO_DO: connection/data object for data/"globalvariable"
#TO-DO: implement recovery using sessionstorage if streamlit lost connection. Needed for mobile
#To_DO: make it singleton?
#TO-DO: integrate video
#TO-DO: make it work with no prior recorded workout
#TO-DO handle multi users/profil to get sessions?

#To-DO: "template" for shared data between exercise (name, equipment,etc.)
#Bug: if pressed create workout or resume workout, can still press the other button (need to disable selection)
#TO-DO: use true instead of 0 1 when getting and storing from gsheet?
#TO-DO: use on change on dataEditor to update Exercise attributes https://discuss.streamlit.io/t/streamlit-st-data-editor-access-edited-rows-dictionary/60286 can't do callback within form. either remove forms or drop the idea

#To-do: set users, then propose potential session based on user
#metadata management, create new exercise, new session

from streamlit_browser_storage import LocalStorage
#s = LocalStorage(key="exercise_data")

def initSessionState():
    if 'showDataClicked' not in st.session_state:
        st.session_state.showDataClicked = False
    if st.session_state.showDataClicked:
        showDataToSend()
    if 'workoutSessionClicked' not in st.session_state:
        st.session_state.workoutSessionClicked = False

    if 'createWorkoutclicked' not in st.session_state:
        st.session_state.createWorkoutclicked = False

    if 'resumeWorkoutclicked' not in st.session_state:
        st.session_state.resumeWorkoutclicked=False
    if 'title' not in st.session_state:
        st.session_state.title = "Gym Tracker"


class CacheData(ABC):
    #def __init__(self):
    @abstractmethod
    def buildData(self):
        pass

class ConnectToDB():
    def __init__(self,dbType="gsheet"):
        self.dbType = dbType

    def querryAllData(self):
        match self.dbType:
                    case "gsheet":
                        self.conn = st.connection("gsheets", type=GSheetsConnection)
                        queryString="Select * FROM Raph WHERE Session IS NOT NULL"
                        self.dfAllData = pd.DataFrame(self.conn.query(queryString))
    
    def setCaches(self):
        lastWorkOutRecord = self.dfAllData[-1:]#duckdb.query("SELECT Date, Session FROM dataframe").to_df().tail(1) #issue being when there is 2 sessions on the same day, it gets order wrongly
        lastWorkOutDate =  lastWorkOutRecord["Date"].iloc[0]
        lastWorkoutSession =  lastWorkOutRecord["Session"].iloc[0]
        dfAllData = self.dfAllData
        query = "SELECT Count(Completed) as NbrUncompleted, Max(Date) as Date, Max(Session) as Session FROM dfAllData WHERE Completed = " + str(False) + " AND Date ='" + str(lastWorkOutDate) +"'"
    
        infoUncompletedSet = duckdb.query(query).to_df()
    
        nbrUncompletedSets = infoUncompletedSet.count()["NbrUncompleted"]
        completedSet = duckdb.query("SELECT * FROM dfAllData WHERE NOT (Session = '" + str(infoUncompletedSet["Session"][0]) + "' AND Date = '" + str(infoUncompletedSet["Date"][0]) + "')").to_df()

        uncompletedSet = {}
        if nbrUncompletedSets > 0:
            uncompletedSet = duckdb.query(f"SELECT * FROM dfAllData WHERE Session = '{lastWorkoutSession}' AND Date = '" + str(infoUncompletedSet["Date"][0]) + "'").to_df()
        self.completedSet = completedSet
        self.uncompletedSet = uncompletedSet
        self.lastWorkoutSession = lastWorkoutSession
        self.lastWorkOutDate = lastWorkOutDate

        def setDataTemplate(self, fieldExerciseTemplate=["Session", "Exercise", "Sets x Reps", "Equipment", "Lbs", "Actual Reps", "Notes", "Total Lbs", "Primary Muscles", "Secondary Muscles", "Sets Completion", "Completed", "Date", "user"]):
            self.fieldExerciseTemplate = fieldExerciseTemplate
    def updateDB(self,dataToUpdate):
        match self.dbType:
            case "gsheet":   
                self.conn.update(worksheet="Raph",data=pd.DataFrame(self.fixGoogleFormulainAllDataSet(dataToUpdate)))

    def fixGoogleFormulainAllDataSet(self, dataToSend):
        #st.write(dataToSend)
        dataToSend = pd.concat([pd.DataFrame(self.completedSet), pd.DataFrame(dataToSend)], ignore_index=True)
        setSize = len(dataToSend.get("Sets x Reps"))
        initSetxReps = []
        initEquip =[]
        initPrimaryMuscles = []
        initSecondaryMuscles = []
        initTotalLbs = []
        for i in range(setSize):
            initSetxReps.append(f"=VLOOKUP(B{i+2},Exercise!A:C,3,False)")
            initEquip.append(f"=VLOOKUP(B{i+2},Exercise!A:B,2,False)")
            initTotalLbs.append(f"=SUM(SPLIT(F{i+2},\",\"))*E{i+2}")
            initPrimaryMuscles.append(f"=VLOOKUP(B{i+2},Exercise!A:E,4,False)")
            initSecondaryMuscles.append(f"=VLOOKUP(B{i+2},Exercise!A:E,5,False)")
        dataToSend["Sets x Reps"] = initSetxReps
        dataToSend["Equipment"] = initEquip
        dataToSend["Total Lbs"] = initTotalLbs
        dataToSend["Primary Muscles"] = initPrimaryMuscles
        dataToSend["Secondary Muscles"] = initSecondaryMuscles

        return dataToSend

class Session:#could have unique instances
    def __init__(self, name, exercises=[], user="Raphael", previousSession = None):#, date=datetime.today().strftime('%Y/%m/%d')):
        self.name = name
        self.user = user
        self.exercises = exercises
        self.previousSession = previousSession

    def getDataToImport(self,importType="googlesheet"):
        if importType=="googlesheet":
            dataToImport =[]

            fieldsToImport = ["Session", "Exercise", "Sets x Reps", "Equipment", "Lbs", "Actual Reps", "Notes", "Total Lbs", "Primary Muscles", "Secondary Muscles", "Sets Completion", "Completed", "Date", "User"]
            for exercise in self.exercises:
                exercise.updateFromFormSubmit()
                for i in range(len(exercise.setsCompletion)):
                    if i == 0:
                        setsCompletion = str(int(exercise.setsCompletion[i]))
                    else:
                        setsCompletion = setsCompletion + "," + str(int(exercise.setsCompletion[i]))

                rowToImport = [self.name, exercise.name, f"{exercise.sets} x {exercise.reps}", exercise.equipment, exercise.lbs, ",".join(exercise.actualReps), exercise.note, exercise.totalLbs, exercise.primarymuscles, exercise.secondarymusles, setsCompletion, int(exercise.completed), exercise.date, exercise.user]
                dataToImport.append(rowToImport)
        return pd.DataFrame(np.array(dataToImport), columns=fieldsToImport)

    def updateExercisesPreviousInfo(self):
        for i in range(len(self.exercises)):
            self.exercises[i].updatePreviousInfo(self.previousSession.exercises[i]) #To-DO should match based on name to avoid diferent set size if new exercise added


    def createNewSession(self):
        newExercises = []
        for i in range(len(self.exercises)):
            newExercises.append(self.exercises[i].createNewExercise())
        return Session(self.name,newExercises, user=self.user,previousSession=self)

    def writeForm(self):
        with st.form("my_form"):
            for exercise in self.exercises:
                exercise.writeForForm()
            st.form_submit_button('Submit', on_click=click_Submitbutton, args=[self])
        
    def fromExerciseData(cls,exerciseData):
        exercises = []
        for index, row in exerciseData.iterrows():
            setsCompletion = row["Sets Completion"].split(",")

            for i in range(len(setsCompletion)):
                setsCompletion[i]=int(setsCompletion[i]) > 0

            exercises.append(Exercise(row["Exercise"], row["Sets x Reps"].split(" x ")[0], row["Sets x Reps"].split(" x ")[1], row["Equipment"], row["Lbs"], row["Primary Muscles"], row["Secondary Muscles"], row["Notes"], row["Actual Reps"].split(","), setsCompletion, int(row["Completed"])>0, row["Date"], row["User"]))
            sessionName = row["Session"] #TO-DO to improve for performance and in case there is several sessions in the dataset

        return cls(sessionName,exercises)
    @classmethod
    def fromAllData(cls, allData, resume=False, session = None):
        if resume: #create 2 sessions, the last uncompleted and the previous completed one, then link them
            lastWorkOutRecord = allData[-1:]
            lastWorkOutDate =  lastWorkOutRecord["Date"].iloc[0] #TO-DO don't use iloc
            lastWorkoutSession =  lastWorkOutRecord["Session"].iloc[0]
            query = "SELECT Count(Completed) as NbrUncompleted, Max(Date) as Date, Max(Session) as Session FROM allData WHERE Completed = " + str(False) + " AND Date ='" + str(lastWorkOutDate) +"'"
            infoUncompletedSet = duckdb.query(query).to_df()
            nbrUncompletedSets = infoUncompletedSet.count()["NbrUncompleted"]
            
            uncompletedSet = {}
            
            if nbrUncompletedSets > 0:
                uncompletedSet = duckdb.query(f"SELECT * FROM allData WHERE Session = '{lastWorkoutSession}' AND Date = '" + str(infoUncompletedSet["Date"][0]) + "'").to_df()
                previousCompletedSessions = duckdb.query(f"SELECT * FROM allData WHERE Session = '{lastWorkoutSession}' AND Date != '" + str(infoUncompletedSet["Date"][0]) + "'").to_df()
                previousCompletedSessionInfo = previousCompletedSessions[-1:]
                previousWorkOutDate =  previousCompletedSessionInfo["Date"].iloc[0] #TO-DO don't use iloc
                queryString = f"SELECT * FROM allData WHERE Session = '{lastWorkoutSession}' AND Date = '" + str(previousWorkOutDate) + "'"
                previousWorkOutData = duckdb.query(queryString).to_df()
                
                previousSession = Session.fromExerciseData(cls,previousWorkOutData)
                resumeSession = Session.fromExerciseData(cls,uncompletedSet)
                resumeSession.previousSession=previousSession
                resumeSession.updateExercisesPreviousInfo()
                return resumeSession

            else:
                st.write("wrong parameter, no Session to resume")
            


            completedSet = duckdb.query("SELECT * FROM allData WHERE NOT (Session = '" + str(infoUncompletedSet["Session"][0]) + "' AND Date = '" + str(infoUncompletedSet["Date"][0]) + "')").to_df()

        else: #create session based on the previous similar session.
            if session!= None:
                queryString=f"Select Max(Date) as LastDate, Count(Date) as NbrExercise FROM allData WHERE Session='{session}' Group By Date ORDER BY LastDate Desc;"
                lastWorkoutDate = duckdb.query(queryString).to_df()["LastDate"][0]
                queryString=f"Select * FROM allData WHERE Session='{session}' AND Date='{lastWorkoutDate}';"
                previousSessionData = duckdb.query(queryString).to_df()

                newSession = Session.fromExerciseData(cls,previousSessionData).createNewSession() #to-do create an explicit function 

                return newSession

            else:
                st.write("wrong parameters to create a session")


        if LastWorkoutDate!=None:
            queryString=f"Select Max(Date) as LastDate, Count(Date) as NbrExercise FROM allData WHERE Session='{session}' AND Date!='{LastWorkoutDate}' Group By Date ORDER BY LastDate Desc;"
        else:
            queryString=f"Select Max(Date) as LastDate, Count(Date) as NbrExercise FROM allData WHERE Session='{session}' Group By Date ORDER BY LastDate Desc;"
        
        lastWorkoutDate = duckdb.query(queryString).to_df()["LastDate"][0]
        if session is not None:
            queryString=f"Select * FROM allData WHERE Session='{session}' AND Date='{lastWorkoutDate}';"
            exerciseData = duckdb.query(queryString).to_df()



        #self.date = date

class ExerciseTemplate:
    def __init__(self, name, reps, equipments, primarymuscles, secondarymusles):
        self.name = name
        self.reps = reps
        self.sets = sets
        self.equipments = equipments
        self.primarymuscles = primarymuscles
        self.secondarymusles = primarymuscles
class Exercise:
    def __init__(self,name,sets,reps, equipment, lbs, primarymuscles, secondarymusles,note,actualReps,setsCompletion,completed, date, user, session=None, previousExercise = None):#to-do remove all previous but exercise from constructor
        self.name = name
        self.sets = int(sets)
        self.reps = reps
        self.equipment = equipment
        self.lbs = lbs
        self.primarymuscles = primarymuscles
        self.secondarymusles = primarymuscles
        self.note = note
        self.actualReps = actualReps
        self.setsCompletion = setsCompletion
        self.completed = completed
        self.date = date
        self.user = user
        self.totalLbs = self.setTotalLbs()
        self.session = session
        self.previousExercise = previousExercise
        if self.previousExercise != None:
            self.previousNote=self.previousExercise.note
            self.previousLbs=self.previousExercise.lbs
            self.previousTotalLbs=self.previousExercise.totalLbs 
    
    def updatePreviousInfo(self,previousExercise):
        self.previousExercise = previousExercise
        self.previousNote = (self.previousExercise).note
        self.previousLbs = self.previousExercise.lbs
        self.previousTotalLbs = self.previousExercise.totalLbs
    def updateFromFormSubmit(self):
        compactExcerciseName = self.name.replace(" ", "")
        
        self.note = st.session_state.get(f"input{compactExcerciseName}")
        edited_rows=st.session_state.get(f"data_editor{compactExcerciseName}").get("edited_rows")
        if edited_rows != {}:
            for j in range(self.sets):
                if edited_rows.get(j, None) is not None:
                    if edited_rows[j].get("Rep", None) is not None:
                        self.actualReps[j] = edited_rows.get(j).get("Rep")
                    if edited_rows[j].get("Weight", None) is not None:
                        self.lbs = edited_rows.get(j).get("Weight")
                    if edited_rows[j].get("Done", None) is not None:
                        self.setsCompletion[j] = edited_rows.get(j).get("Done")>0
        self.completed = True
        for setCompletion in self.setsCompletion:
            if setCompletion == False:
                self.completed = False

    def createNewExercise(self):
        return Exercise(self.name,self.sets,self.reps, self.equipment, self.lbs, self.primarymuscles, self.secondarymusles,None,self.actualReps,[False,False,False],False, datetime.today().strftime('%Y/%m/%d'), self.user, self.session, self)

    def setTotalLbs(self):
        totalLbs = 0
        for i in range(len(self.setsCompletion)):
            if int(self.setsCompletion[i])>0:
                totalLbs = totalLbs + int(self.actualReps[i])*self.lbs
        return totalLbs
    def writeForForm(self):
        with st.container():
            excerciseName = self.name
            compactExcerciseName = excerciseName.replace(" ", "")
            noteValue = self.note
            aDone = self.setsCompletion
            nbrSets = self.sets
            actualReps = self.actualReps
            with st.expander(excerciseName, expanded=not self.completed):
                col1, col2 = st.columns(2)
                col1.subheader(f"{excerciseName}: {nbrSets} x {self.reps}")
                weight = self.lbs
                aDF = []
                for j in range(nbrSets):
                    done=int(aDone[j])>0
                    aDF.append(dict(Weight=weight,
                        Rep=actualReps[j],
                        Done=done,
                        )
                    )
                
                editedDF=col1.data_editor(pd.DataFrame(aDF, index=(range(nbrSets))), key=f"data_editor{compactExcerciseName}", hide_index=True, num_rows="fixed")
                text_input=col1.text_input(label="Notes", value=noteValue, key=f"input{compactExcerciseName}", placeholder="Enter Notes")
                with col2.expander("Last Session Info", expanded=True):
                    notes = self.previousNote
                    lbs = self.previousLbs
                    totalLbs = self.previousTotalLbs
                    if notes != None:
                        st.write(f"Notes: {notes}")                                
                    st.write(f"Lbs: {lbs}")
                    st.write(f"Total Lbs: {totalLbs}")
                with col2.expander("Description", expanded=False):
                    st.write(f"Equipment: {self.equipment}")
                    st.write(f"Primary Muscles: {self.primarymuscles}")
                    st.write(f"Secondary Muscles: {self.secondarymusles}")
 
initSessionState()
st.title(st.session_state.title)
st.set_page_config(page_title="Gym Tracker", page_icon=":mechanical_arm:", layout="wide")

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

#st.button("Create Data", on_click=createClick, key="createData")
#st.button("Show Data", on_click=showDataClick, key="showData")
#st.button("Hide Data", on_click=hideDataClick, key="hideData")
#st.button("Clear Data", on_click=clearDataClick, key="clearData")



cachedData = ConnectToDB("gsheet")
cachedData.querryAllData()
cachedData.setCaches()

def click_button():
    st.session_state.workoutSessionClicked = True

def createWorkoutclick_button():
    st.session_state.title = "Create Workout"
    st.session_state.createWorkoutclicked = True

def resumeWorkoutclick_button():
    st.session_state.title = "Resume Workout"
    st.session_state.resumeWorkoutclicked = True

def click_Submitbutton(session):
    st.session_state.createWorkoutclicked = True

    st.session_state.title = "Gym Tracker"
    dataToSend = session.getDataToImport()#updateDataToSend(exerciseDataFromForm)
    st.write(dataToSend)
    
    #dataToSend = fixGoogleFormulainAllDataSet(dataToSend, cachedData.completedSet)

    cachedData.updateDB(dataToSend)
    #conn = st.connection("gsheets", type=GSheetsConnection)
    #conn.update(worksheet="Raph",data=())
    
    st.session_state.createWorkoutclicked = False
    st.session_state.resumeWorkoutclicked=False

    st.cache_data.clear()
    st.success("Workout data submitted successfully!")

if st.session_state.createWorkoutclicked==False and not st.session_state.resumeWorkoutclicked==True:
    createWorkOut = st.button("Create Workout", on_click=createWorkoutclick_button, key="createWorkout")

if st.session_state.resumeWorkoutclicked==False and len(cachedData.uncompletedSet) != 0:
    resumeWorkOut = st.button("Resume Workout", on_click=resumeWorkoutclick_button, key="resumeWorkout")        

if st.session_state.resumeWorkoutclicked==True:
    sessionToDisplay = Session.fromAllData(cachedData.dfAllData,resume=True).writeForm()

if st.session_state.createWorkoutclicked:
    st.session_state.resumeWorkoutclicked=False
    options = ["A", "B"]
    defaultOption = options[(options.index(cachedData.lastWorkoutSession)+1)%len(options)]
    selection = st.pills("Workout", options, default = defaultOption, selection_mode="single")
    if selection is not None:
        sessionToDisplay = Session.fromAllData(cachedData.dfAllData,session=selection).writeForm()

