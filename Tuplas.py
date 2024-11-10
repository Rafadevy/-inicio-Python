tupla = ("zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", 
         "onze", "doze", "treze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove", "vinte")
while True:
    nm = int(input("DIGITE UM NUMERO ENTRE 0 E 20: "))
    if 0 <= nm <= 20:
        print(f"Você digitou o número {tupla[nm]}")

    resp = str(input("QUER CONTINUAR [S/N]")).upper().strip()
    while resp not in "SN":
        resp = str(input("QUER CONTINUAR [S/N]")).upper().strip()
    if resp == "N":
        break

#---------------------

tupla = ("Botafogo","Palmeiras","Fortaleza","Flamengo","Sao Paulo","Corinthias","Atletico GO","Cuiaba","Vitoria")

print(f"Lista de times {tupla}")

a = tupla[0:5]
b = tupla[-4:]

print(a)
print(b)
print(f"{sorted(tupla)}")
print(f"o vitoria esta na {tupla.index("Vitoria")} colocaçao")


#-------------------------


import random
numeros = tuple((random.randint(1,10)) for _ in range(5))

print(f"Numeros gerados: {numeros}")

print("menor",min(numeros))
print("maior",max(numeros))


tupla = ()
for _ in range (5):
    numeros = (random.randint(1,10))
    tupla += (numeros,)
print("Numeros gerados:",tupla)
print("menor",min(tupla))
print("maior",max(tupla))

#------------------------------

tupla = ()
for c in range (4):
    numeros = int(input("digite um numeros:"))
    tupla += (numeros,)
print(tupla)
print(f"O valor 9 apareceu {tupla.count(9)} vezes")
if 3 in tupla:
    print(f"O valor 3 apareceu na {tupla.index(3)} posiçao")
else:
    print("O valor 3 nao foi encontrado na tupla")
print("Numeros pares na tupla:",end=" ")
for n in tupla:
    if n % 2 == 0:
        print(n,end=" ")
