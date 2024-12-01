def two_sum(nums, target):
    num_to_index = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_to_index:
            return [num_to_index[complement], i]
        num_to_index[num] = i
    return []

nums = [2, 7, 11, 15]
target = 9

print(two_sum(nums, target))

#---------------------------
class Solution:
    def isPalindrome(self, x: int) -> bool:
        str_x = str(x)
        inverso = str_x[::-1]
        return str_x == inverso

solution = Solution()

print(solution.isPalindrome(121))
print(solution.isPalindrome(-121))
print(solution.isPalindrome(10))

def romanoToInt(s: str) -> int:
    roman_to_int = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50,
            'C': 100, 'D': 500, 'M': 1000
        }
    total = 0
    prev_value = 0

    for char in s:
        value = roman_to_int[char]
        if value > prev_value:
            total += value - 2 * prev_value
        else:
            total += value
        prev_value = value

  #-------------------------------

  def somar_valores_impares(y):
   soma = 0
   for c in range (1,y,2):
      if c % 3 == 0:
         soma += c 
   return soma

y = int(input("ate aonde somar os multiplos de 3: "))

print(f"a soma dos valores é : {somar_valores_impares(y)}") 
    
    return total

s = input("Digite um algarismo romano: ")
print(romanoToInt(s))

#--------------------------------

def soma(n1, n2):
  return n1 + n2

def multiplicaçao(n1, n2):
  return n1 * n2

def subtraçao(n1, n2):
  return n1 - n2

def divisao(n1, n2):
  return n1 / n2

n1 = float(input("digite um numero: "))
n2 = float(input("digite outro numero: "))

recept = (input("Qual operaçao voce quer fazer? (somar,subtrair,dividir,multiplicar) ")).strip() .lower()

if recept == "somar":
  print(f"Resultado: {soma(n1, n2)}")

elif recept == "subtrair":
  print(f"Resultado : {subtraçao(n1,n2)}")

elif recept == "multiplicacar":
  print(f"Resultado: {multiplicaçao(n1, n2)}")

elif recept == "dividir":
  print(f"Resultado: {divisao(n1, n2)}")
  
else:
  print("Operação inválida.")

#-------------------------------------

import random
def gerarnumeros():
    return random.randint(1,60)

def gerar_jogo():
    numeroSort = []
    while len(numeroSort) < 6:
        numero = gerarnumeros()
        if numero not in numeroSort:
            numeroSort.append(numero)
    return numeroSort

def main():
    jogos = []
    quantos_jogos = int(input("Quantos jogos voce quer: "))

    for i in range (quantos_jogos):
        jogo = gerar_jogo()
        jogos.append(jogo)
    
    for idx, jogo in enumerate(jogos, start=1): 
        print(f"Jogo {idx}: {sorted(jogo)}") 
if __name__ == "__main__": main()
