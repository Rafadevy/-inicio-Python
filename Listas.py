lista = []
for c in range (5):
    nmr = int(input("Digite um numero: "))
    lista.append(nmr)

maior_valor = max(lista)
menor_valor = min(lista)

pos_maior = lista.index(maior_valor)
pos_menor = lista.index(menor_valor)

print(f"O maior valor digitado foi {maior_valor} na posição {pos_maior}")
print(f"O menor valor digitado foi {menor_valor} na posição {pos_menor}")

listanum = []
mai = 0
men = 0

for c in range (5):
    listanum.append(int(input("Digites os um numero para a posiçao {c}:  "))) 
    print(f"Voce digitou os valores{listanum}")
    if c == 0:
        mai = men = listanum[c]
    else:
        if listanum[c] > mai:
            mai = listanum[c]
        if listanum[c] < men:
            men = listanum[c]


#---------------------------


palavras = ("item", "gratuito", "proibido", "rubrica", "recorde", "pudico", "menu", "ali", "raiz", "higiene")
for p in palavras:
    print(f"\nNa palavra {p.upper()} temos",end=" ")
    for letra in p:
        if letra.lower() in "aeiou":
            print(letra,end=" ")
print(f"Voce digitou os valores: {listanum}")
print(f"O maior valor é: {mai} nas posiçoes ", end=" ")
for i, v in enumerate(listanum):
    if v == mai:
        print(f"{i}")
print(f"O menor valor é: {men}nas posiçoes", end=" ")
for i, v in enumerate(listanum):
    if v == men:
        print(f"{i}")

#----------------------------


lista = []
while True:
    nmr = int(input("Digite um numero para cadastrar: "))
    if nmr not in lista: 
        lista.append(nmr) 
    else: print(f"O número {nmr} já está na lista e não será adicionado.")
    resp = " "
    while resp not in "SN":
        resp = str(input("QUER CONTINUAR? [S/N] ")).upper().strip()
    
    if resp == "N":
        break

print(f"Voce cadastrou os seguntes valores: {lista}", end=" ")


#--------------------------

lista = [1,8,5,6,7,12]

def bullbe_sort (arr):
    n = len (arr)
    for i in range (n):
        for j in range(0,n-i-1):
            if arr[j] > arr[j+1]:  
                arr[j], arr[j+1] = arr[j+1], arr[j]  
    return arr
print(bullbe_sort(lista))

s = "Data scinecy academi"

print(s[0:])
#.lower
#.strip
#.upper
#.split

lista_1 = ["arroz","feijao","macarrao","salada","suco"]
print(lista_1)
lista_2 = [20,2200,"analise de dados"]
print(lista_2)

item1 = lista_2[0]
item2 = lista_2[1]
item3 = lista_2[2]

print(item2)

lista_2[1] = "chocolate"

print(lista_2)

del lista_1 [2]

print(lista_1)

listas = [[1,2,3],[10,15,20],[10,9,2,3.9]]


a = listas[0]

print(a)

b = a[0]

print(b)

lista_11 = listas [1]

print(lista_11)

valor_1_0 = lista_11[0]

print(valor_1_0)

a = listas[0][0]

print(a)

b = listas[1][2]

print(b)

c = listas[0][2] + 10

print(c)

e = b * listas[2][0]

print(e)

list1 = [1,3,4,5,]

list2 = [3,4,5,3,2]

# soma de listas vvv
lista_total = list1 + list2
print (lista_total)

lista_teste_1 = [100,40,34]
print(1 in lista_teste_1)

#FUNÇOES BUILT-IN

lista_numeros = [99,88,45,34,23,22]

comprimento = len(lista_numeros)
#maior valor
max = max(lista_numeros)
#menor valor
min = min(lista_numeros)

print(comprimento,max,min)

lista_funcoes = ["Analise de dados", "Ciencia de dados", "Engenharia de dados"] 

print(lista_funcoes)

lista_funcoes.append("Engenheiro de IA")

print(lista_funcoes)

cont = lista_funcoes.count("Engenheiro de IA")

print(cont)

a = []
a.append(10)
print(a)

old_list = [1,2,55,6,7,]

new_list = []

for item in old_list :
    new_list.append(item)
    print(new_list)
 
cidades = ["Recife","Sao paulo","Goias","Londrina"]
cidades.extend(["Rio de Janeiro","Natal"])
print(cidades)

cidades.insert(2,110)
print(cidades)

cidades.reverse()
print(cidades)

x = [3,5,7,8,4,9,1,2]
x.sort()
print(x)

#reverse()
#sort()
#remove()
