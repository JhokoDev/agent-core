<?php

class Produto {
    private string $nome;
    private float $preco;

    public function __construct(string $nome, float $preco) {
        $this->nome = $nome;
        $this->setPreco($preco);
    }

    public function getNome(): string {
        return $this->nome;
    }

    public function getPreco(): float {
        return $this->preco;
    }

    // O encapsulamento protege contra preços negativos
    public function setPreco(float $preco): void {
        if ($preco >= 0) {
            $this->preco = $preco;
        } else {
            throw new Exception("O preço não pode ser negativo.");
        }
    }

    public function aplicarDesconto(float $porcentagem): void {
        if ($porcentagem > 0 && $porcentagem <= 100) {
            $desconto = ($this->preco * $porcentagem) / 100;
            $this->preco -= $desconto;
        }
    }
    
    public function exibirDetalhes(): string {
        return "Produto: {$this->nome} | Preço: R$ " . number_format($this->preco, 2, ',', '.');
    }
}
?>