import mysql.connector


class DB():
    cur = False
    con = False
    maxSimTime = 0
    maxAge = 0
    timeBuffer = 0
    keys_individuals = []
    keys_traces = []
    keys_offspring = []
    tablePrefix = ""

    def __init__(self, connectionString, tablePrefix, maxSimTime=0, maxAge=0):
        self.maxSimTime = maxSimTime
        self.maxAge = maxAge
        self.tablePrefix = tablePrefix

        components = connectionString.split("@")
        if len(components) != 2:
            raise ValueError("connection string did have more or less than 1 @ symbol")

        auth = components[0].split(":")
        hostdb = components[1].split("/")
        if len(auth) != 2:
            raise ValueError("connection string did have more or less than 1 : symbol")
        if len(hostdb) != 2:
            raise ValueError("connection string did have more or less than 1 / symbol")

        config = {
            'user': auth[0],
            'password': auth[1],
            'host': hostdb[0],
            'database': hostdb[1],
            'raise_on_warnings': True,
        }

        self.con = mysql.connector.connect(**config)
        self.cur = self.con.cursor(dictionary=True)

    def test(self):
        # TODO: test db connection
        pass

    def close(self):
        self.con.close()

    def onlyGetIDs(self, results):
        out = []
        for indiv in results:
            out.append(indiv["id"])
        return out

    def getHNtodos(self):
        """ retrieve individuals that need to be created (that only exist in the database so far)
        :return: list with strings (individual names)
        """
        self.flush()
        self.cur.execute("SELECT * FROM "+self.tablePrefix+"_individuals AS i " +
                         "WHERE i.hyperneated = 0 AND born < '" + str(self.maxSimTime) + "'")
        results = self.cur.fetchall()
        return self.onlyGetIDs(results)

    def getVoxTodos(self, resubmit=False):
        """ retrieve individuals that need to be voxelyzed
        :return: list with strings (individual names)
        """
        searchString = "SELECT * FROM "+self.tablePrefix+"_individuals AS i " + \
                       "WHERE i.hyperneated = 1"
        if (resubmit):
            searchString += " AND i.vox_submitted = 1 AND i.voxelyzed = 0"
        else:
            searchString += " AND i.vox_submitted = 0"
        self.flush()
        self.cur.execute(searchString)
        results = self.cur.fetchall()
        return self.onlyGetIDs(results)

    def getParents(self, indiv):
        """ get parents, if they exist, for a given individual
        :return: list of strings (parent IDs), length of this list is either 0, 1 or 2, for no parents, has been mutated from 1 parent and was created by mating,
        """
        self.flush()
        self.cur.execute("SELECT * FROM "+self.tablePrefix+"_offspring AS o " +
                         "WHERE o.child_id = " + str(indiv))
        result = self.cur.fetchone()
        if result == None:
            return []
        else:
            out = [str(result['parent1_id'])]
            if (result['parent2_id'] != None):
                out.append(str(result['parent2_id']))
            return out


    def markAsHyperneated(self, indiv):
        """ marks the individual as been processed by HyperNEAT. I.e. an actual file was created from database
        :param indiv: string, ID of an individual
        :return: None
        """
        self.cur.execute("UPDATE "+self.tablePrefix+"_individuals SET hyperneated = 1 WHERE id = " + str(indiv) + ";")

    def markAsVoxelyzed(self, indiv):
        """ marks the individual as been actually processed by Voxelyze
        :param indiv: string, ID of an individual
        :return: None
        """
        self.cur.execute("UPDATE "+self.tablePrefix+"_individuals SET voxelyzed = 1 WHERE id = " + str(indiv) + ";")

    def markAsVoxSubmitted(self, indiv):
        """ marks the individual as been submitted to Lisa
        :param indiv: string, ID of an individual
        :return: None
        """
        self.cur.execute("UPDATE "+self.tablePrefix+"_individuals SET vox_submitted = 1 WHERE id = " + str(indiv) + ";")

    def markAsPreprocessed(self, indiv):
        """ marks the individual as successfully mates, trace file moved and corrected
        :param indiv: string, ID of an individual
        :return: None
        """
        self.cur.execute("UPDATE "+self.tablePrefix+"_individuals SET postprocessed = 1 WHERE id = " + str(indiv) + ";")

    def markAsDead(self, indiv):
        """ marks the individual as unusable
        :param indiv: string, ID of an individual
        :return: None
        """
        self.cur.execute("UPDATE "+self.tablePrefix+"_individuals SET postprocessed = 1, hyperneated = 1, " + \
                         "voxelyzed = 1, vox_submitted =1 WHERE id = " + str(indiv) + ";")

    def dropTables(self):
        self.cur.execute("SET sql_notes = 0")
        self.cur.execute("DROP TABLE IF EXISTS "+self.tablePrefix+"_individuals")
        self.cur.execute("DROP TABLE IF EXISTS "+self.tablePrefix+"_traces")
        self.cur.execute("DROP TABLE IF EXISTS "+self.tablePrefix+"_offspring")
        self.cur.execute("DROP TABLE IF EXISTS "+self.tablePrefix+"_jobs")
        self.cur.execute("SET sql_notes = 1")
        self.flush()

    def createTables(self):
        self.cur.execute("SET sql_notes = 0")
        self.cur.execute("CREATE TABLE IF NOT EXISTS " +
                         self.tablePrefix+"_individuals " +
                         "(id INT NOT NULL AUTO_INCREMENT, " +
                         "born FLOAT NOT NULL, " +
                         "hyperneated TINYINT(1) DEFAULT 0 NOT NULL, " +
                         "vox_submitted TINYINT(1) DEFAULT 0 NOT NULL, " +
                         "voxelyzed TINYINT(1) DEFAULT 0 NOT NULL, " +
                         "postprocessed TINYINT(1) DEFAULT 0 NOT NULL, " +
                         "PRIMARY KEY (id) )")
        self.cur.execute("CREATE TABLE IF NOT EXISTS " +
                         self.tablePrefix+"_traces " +
                         "(id INT NOT NULL AUTO_INCREMENT, " +
                         "indiv_id INT NOT NULL, " +
                         "ltime FLOAT NOT NULL, " +
                         "x FLOAT NOT NULL, " +
                         "y FLOAT NOT NULL, " +
                         "z FLOAT NOT NULL, " +
                         "fertile TINYINT(1) DEFAULT 1 NOT NULL, " +
                         "PRIMARY KEY (id) )")
        self.cur.execute("CREATE TABLE IF NOT EXISTS " +
                         self.tablePrefix+"_offspring " +
                         "(id INT NOT NULL AUTO_INCREMENT, " +
                         "parent1_id INT NOT NULL, " +
                         "parent2_id INT, " +
                         "child_id INT NOT NULL, " +
                         "ltime FLOAT NOT NULL, " +
                         "PRIMARY KEY (id) )")
        self.cur.execute("CREATE TABLE IF NOT EXISTS " +
                         self.tablePrefix+"_jobs " +
                         "(id INT NOT NULL AUTO_INCREMENT, " +
                         "jname VARCHAR(20), " +
                         "cmd TEXT, " +
                         "start TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, " +
                         "done DATETIME DEFAULT NULL, " +
                         "individuals TEXT DEFAULT NULL, " +
                         "PRIMARY KEY (id) )")
        self.cur.execute("SET sql_notes = 1")
        self.flush()

    def createIndividual(self, born, x, y):
        self.cur.execute("INSERT INTO "+self.tablePrefix+"_individuals VALUES (NULL, '" + str(born) + "', 0, 0, 0, 0);")
        individual_id = self.getLastInsertID()
        self.cur.execute(
            "INSERT INTO "+self.tablePrefix+"_traces VALUES (NULL, " + individual_id + ", '" + str(born) + "', '" + str(x) + "', '" + str(
                y) + "', 0, 1);")
        self.flush()
        print ("created individual: " + individual_id)

        return individual_id

    def addTraces(self, id, traces):
        firstTrace = self.getFirstTrace(id)
        insertSting = "INSERT INTO "+self.tablePrefix+"_traces VALUES (NULL, %s, %s, %s, %s, %s, 1);"
        self.cur.executemany(insertSting, traces)
        self.cur.execute("DELETE FROM "+self.tablePrefix+"_traces WHERE id={id};".format(id=firstTrace["id"]))
        self.flush()

    def getIndividual(self, id):
        self.flush()
        self.cur.execute("SELECT * FROM "+self.tablePrefix+"_individuals AS i WHERE i.id = '" + str(id) + "' ")
        # return dict(zip(self.keys_individuals, self.cur.fetchone()))
        return self.cur.fetchone()

    def getTraces(self, id):
        self.flush()
        self.cur.execute("SELECT * FROM "+self.tablePrefix+"_traces AS t WHERE t.indiv_id = '" + str(id) + "' ")
        return self.cur.fetchall()


    def getFirstTrace(self, id):
        self.flush()
        self.cur.execute("SELECT * FROM "+self.tablePrefix+"_traces AS t WHERE t.indiv_id = '" + str(id) + "' ORDER BY t.id ASC")
        # return dict(zip(self.keys_traces, self.cur.fetchone()))
        return self.cur.fetchone()

    def flush(self):
        self.con.commit()

    def addJob(self, name, cmd, individuals=[]):
        name = name.replace("'", "\\'")
        cmd = cmd.replace("'", "\\'")
        indivs = ""
        if (len(individuals) > 0):
            indivs = ",".join(individuals)
        insertSting = "INSERT INTO "+self.tablePrefix+"_jobs VALUES (NULL, '{name}', '{cmd}', NOW(), NULL, '{indivs}');"
        self.cur.execute(insertSting.format(name = name, cmd = cmd, indivs = indivs))
        self.flush()

    def getJobsWaitingCount(self):
        querySting = "SELECT COUNT(id) FROM "+self.tablePrefix+"_jobs WHERE done IS NULL;"
        self.cur.execute(querySting)
        result = self.cur.fetchall()
        return result[0]['COUNT(id)']

    def setJobDone(self, indiv):
        querySting = "UPDATE "+self.tablePrefix+"_jobs SET done=NOW() WHERE individuals LIKE '%{indiv}%';"
        self.cur.execute(querySting.format(indiv = indiv))

    def getLastInsertID(self):
        self.cur.execute("SELECT LAST_INSERT_ID();")
        individual_id = self.cur.fetchone()['LAST_INSERT_ID()']
        return str(individual_id)

    def makeFakeBaby(self, parent1, parent2="NULL"):
        id = self.createIndividual(0, 1, 2)
        self.cur.execute(
            "INSERT INTO "+self.tablePrefix+"_offspring VALUES (NULL, " + str(parent1) + ", " + str(parent2) + ", " + str(id) + ", 0);")
        return id

    def makeBaby(self, parent1, parent2, ltime, infertileSpan):
        x = (parent1["x"] + parent2["x"]) / 2
        y = (parent1["y"] + parent2["y"]) / 2
        id = self.createIndividual(ltime, x, y)
        insertString = "INSERT INTO "+self.tablePrefix+"_offspring VALUES (NULL, {parent1}, {parent2}, {child}, {ltime});"
        self.cur.execute(
            insertString.format(parent1=parent1["indiv_id"], parent2=parent2["indiv_id"], child=id, ltime=ltime))
        self.infertilize(parent1["indiv_id"], ltime, infertileSpan)
        self.infertilize(parent2["indiv_id"], ltime, infertileSpan)
        self.flush()
        return id

    def infertilize(self, parent, start, timespan):
        updateString = "UPDATE "+self.tablePrefix+"_traces SET fertile = 0 WHERE indiv_id = {indiv} AND ltime >= {start} AND ltime < {end}"
        self.cur.execute(updateString.format(indiv = parent, start = start, end = start + timespan))

    def findMate(self, id, timeTolerance=0.0, spaceTolerance=0.01, startTrace=0):
        query = "SELECT t1.*, t2.indiv_id as mate_indiv_id, t2.id as mate_id, t2.ltime as mate_ltime, t2.x as mate_x, t2.y as mate_y, t2.z as mate_z " + \
                "FROM "+self.tablePrefix+"_traces AS t1 INNER JOIN "+self.tablePrefix+"_traces as t2 " + \
                "WHERE t1.indiv_id='{indiv_id}' and t2.indiv_id!='{indiv_id}' " + \
                "AND t1.fertile = 1 AND t2.fertile = 1 " + \
                "AND t1.id > {start} " + \
                "AND t1.ltime >= t2.ltime-{timeTol} AND t1.ltime <= t2.ltime+{timeTol} " + \
                "AND SQRT( POW(t1.x - t2.x,2) + POW(t1.y - t2.y,2) ) <= {spaceTol} " + \
                "LIMIT 1"
        self.cur.execute(query.format(indiv_id=id, timeTol=timeTolerance, spaceTol=spaceTolerance, start=startTrace))
        return self.cur.fetchall()
