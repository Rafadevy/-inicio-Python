estudante_dict = {"Pedro":23,"Ana":24,"Ronaldo":26,"Janaina":19}

print(estudante_dict["Pedro"])
estudante_dict["Marcelo"] = 21
print(estudante_dict)

#estudante_dict.clear()
#del estudante_dict

print(len(estudante_dict))

estudantes = {"Ana":22,"Junior":21,"Lucas":29,"Janaina":19}

#print(estudantes.len())
#print(estudantes.keys())
#print(estudantes.values())
#print(estudantes.items())


#DICIONARIO:
estudantes_2 = {"Ronaldo":20,"Leandro":22,"Adriana":25}
print(estudantes_2)

estudantes.update(estudantes_2)
print(estudantes)

dic1 = {}

#ITEM = par de chave e valor , a chave pode se string e o par pode ser um numero mas nao é recomendavel

dic1["chave"]=2

dic1[10] = 5

dic1[9.23] = "Python"

dic1["teste"] = 10

dic1[10] = "teste"

print(dic1)
