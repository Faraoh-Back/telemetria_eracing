while IFS= read -r line; do
  echo "Enviando: $line"
  cansend can0 "$line"
  # Adicione um pequeno delay se quiser simular um envio mais espaçado
  sleep 0.1 # Ex: espera 10 milissegundos entre cada mensagem
done < sample_can_mess.log