"""Mede a acurácia da classificação da Laya num conjunto pequeno de transcrições rotuladas à mão.

Uso: python avaliar.py [--modelo multilingual]
Rode de novo depois de mexer nas perguntas de classificar.py.
"""

import argparse
from collections import defaultdict

from classificar import classificar

# (gancho, transcrição completa, final, rótulos esperados)
CASOS = [
    ("Você perde clientes todo mês e não sabe por quê?",
     "Você perde clientes todo mês e não sabe por quê? A maioria dos negócios pequenos demora horas para responder no WhatsApp e o cliente desiste. Configure uma mensagem automática, crie respostas prontas e meça o tempo de resposta toda semana. Comenta RESPOSTA que eu te mando o roteiro.",
     "Comenta RESPOSTA que eu te mando o roteiro.",
     {"tipo_gancho": "pergunta", "tem_introducao": "não", "estrutura": "problema-solução", "tipo_final": "palavra-chave para comentar"}),
    ("Oi, gente! Eu sou a Carla e hoje eu vou falar sobre produtividade.",
     "Oi, gente! Eu sou a Carla e hoje eu vou falar sobre produtividade. Primeira dica: acorde no mesmo horário. Segunda dica: deixe o celular longe da cama. Terceira dica: faça a tarefa mais difícil primeiro. Me segue para mais dicas.",
     "Me segue para mais dicas.",
     {"tipo_gancho": "apresentação/introdução", "tem_introducao": "sim", "estrutura": "lista", "tipo_final": "pedido de seguir"}),
    ("Eu fiz 100 mil reais em 30 dias com um produto de 47 reais.",
     "Eu fiz 100 mil reais em 30 dias com um produto de 47 reais. O segredo foi a oferta: eu juntei três bônus e coloquei garantia de sete dias. Se você quer a minha planilha de oferta, o link está na bio.",
     "Se você quer a minha planilha de oferta, o link está na bio.",
     {"tipo_gancho": "resultado com número", "tem_introducao": "não", "tipo_final": "venda direta"}),
    ("Em 2019 eu fui demitido numa segunda-feira.",
     "Em 2019 eu fui demitido numa segunda-feira. Eu tinha dois filhos e nenhuma reserva. Comecei vendendo bolo na porta da empresa onde eu trabalhava. Três anos depois, eu tinha cinco lojas. Disciplina vence talento quando talento não tem disciplina.",
     "Três anos depois, eu tinha cinco lojas. Disciplina vence talento quando talento não tem disciplina.",
     {"tipo_gancho": "história pessoal", "tem_introducao": "não", "estrutura": "história", "tipo_final": "frase de efeito"}),
    ("Todo mundo fala para você acordar às cinco da manhã. Isso é mentira.",
     "Todo mundo fala para você acordar às cinco da manhã. Isso é mentira. O que importa é dormir o suficiente. Pessoas que dormem bem produzem mais do que quem acorda cedo e passa o dia cansado. Na minha opinião, essa moda de acordar cedo faz mais mal do que bem.",
     "Na minha opinião, essa moda de acordar cedo faz mais mal do que bem.",
     {"tipo_gancho": "contraste", "tem_introducao": "não", "estrutura": "opinião", "tipo_final": "sem pedido"}),
    ("O Instagram acabou de lançar uma função nova para Reels.",
     "O Instagram acabou de lançar uma função nova para Reels. Agora você pode testar até quatro capas diferentes e a plataforma escolhe a que tem mais cliques. A função está liberando aos poucos no Brasil. Salva esse vídeo e manda para aquele amigo que posta todo dia.",
     "Salva esse vídeo e manda para aquele amigo que posta todo dia.",
     {"tipo_gancho": "novidade", "tem_introducao": "não", "estrutura": "notícia", "tipo_final": "pedido de salvar ou compartilhar"}),
    ("Como fazer sua primeira venda online em três passos.",
     "Como fazer sua primeira venda online em três passos. Passo um: escolha um problema que você sabe resolver. Passo dois: crie uma página simples com o preço. Passo três: mande para dez pessoas que têm esse problema. Comenta VENDA que eu te mando o modelo da página.",
     "Comenta VENDA que eu te mando o modelo da página.",
     {"tem_introducao": "não", "estrutura": "tutorial passo a passo", "tipo_final": "palavra-chave para comentar"}),
    ("iPhone ou Android para quem está começando a gravar?",
     "iPhone ou Android para quem está começando a gravar? O iPhone tem câmera mais consistente e os aplicativos de edição funcionam melhor. O Android custa menos e tem mais armazenamento pelo mesmo preço. Para quem está começando, o Android intermediário resolve.",
     "Para quem está começando, o Android intermediário resolve.",
     {"tipo_gancho": "pergunta", "tem_introducao": "não", "estrutura": "comparação", "tipo_final": "sem pedido"}),
    ("Most people will never be rich because they hate selling.",
     "Most people will never be rich because they hate selling. Every business is a sales business. If you can't sell, you can't hire, you can't raise money, you can't get customers. Learn to sell, or learn to be broke.",
     "Learn to sell, or learn to be broke.",
     {"tipo_gancho": "provocação", "tem_introducao": "não", "estrutura": "opinião", "tipo_final": "frase de efeito"}),
    ("Hey guys, my name is Alex, and today I'm going to talk about pricing.",
     "Hey guys, my name is Alex, and today I'm going to talk about pricing. Here are three mistakes. One, you charge by the hour. Two, you never raise prices. Three, you give discounts to close. Follow me for more business tips.",
     "Follow me for more business tips.",
     {"tipo_gancho": "apresentação/introdução", "tem_introducao": "sim", "estrutura": "lista", "tipo_final": "pedido de seguir"}),
    ("Your ads aren't working because your offer is weak.",
     "Your ads aren't working because your offer is weak. You keep changing creatives, audiences, budgets, and nothing changes. The problem is that nobody wants what you're selling at that price. Fix the offer: add a guarantee, add bonuses, make it a no-brainer. Comment OFFER and I'll send you my template.",
     "Fix the offer: add a guarantee, add bonuses, make it a no-brainer. Comment OFFER and I'll send you my template.",
     {"tipo_gancho": "problema", "tem_introducao": "não", "estrutura": "problema-solução", "tipo_final": "palavra-chave para comentar"}),
    ("We went from 1 to 32 million dollars in 4 years.",
     "We went from 1 to 32 million dollars in 4 years. The biggest lever was retention. We called every customer in their first week. Churn dropped by half. If you want our full playbook, grab the book at the link in my bio.",
     "If you want our full playbook, grab the book at the link in my bio.",
     {"tipo_gancho": "resultado com número", "tem_introducao": "não", "tipo_final": "venda direta"}),
    ("When I was 23, I lost everything I owned.",
     "When I was 23, I lost everything I owned. I slept on the floor of my gym for months. I learned that nobody is coming to save you. That was the best thing that ever happened to me. Share this with someone who needs to hear it.",
     "That was the best thing that ever happened to me. Share this with someone who needs to hear it.",
     {"tipo_gancho": "história pessoal", "tem_introducao": "não", "estrutura": "história", "tipo_final": "pedido de salvar ou compartilhar"}),
    ("Cold email versus cold calls: which one wins?",
     "Cold email versus cold calls: which one wins? Email scales: you can send a thousand a day. Calls convert better: you get real conversations. Start with calls to learn the pitch, then move to email to scale it.",
     "Start with calls to learn the pitch, then move to email to scale it.",
     {"tipo_gancho": "pergunta", "tem_introducao": "não", "estrutura": "comparação", "tipo_final": "sem pedido"}),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="multilingual")
    args = ap.parse_args()

    regs = [{"gancho": g, "texto": t, "final": f} for g, t, f, _ in CASOS]
    preds = classificar(regs, args.modelo)
    acertos, total = defaultdict(int), defaultdict(int)
    for (g, _, _, esperado), pred in zip(CASOS, preds):
        for campo, valor in esperado.items():
            total[campo] += 1
            if pred[campo] == valor:
                acertos[campo] += 1
            else:
                print(f"  {campo}: esperado '{valor}', veio '{pred[campo]}'  <- {g[:60]}")
    print(f"\nModelo: {args.modelo}")
    for campo in total:
        print(f"  {campo:16s} {acertos[campo]}/{total[campo]}")


if __name__ == "__main__":
    main()
