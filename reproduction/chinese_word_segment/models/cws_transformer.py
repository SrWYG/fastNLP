


"""
使用transformer作为分词的encoder端

"""

from torch import nn
import torch
from fastNLP.modules.encoder.transformer import TransformerEncoder
from fastNLP.modules.decoder.CRF import ConditionalRandomField,seq_len_to_byte_mask
from fastNLP.modules.decoder.CRF import allowed_transitions

class TransformerCWS(nn.Module):
    def __init__(self, vocab_num, embed_dim=100, bigram_vocab_num=None, bigram_embed_dim=100, num_bigram_per_char=None,
                 hidden_size=200, embed_drop_p=0.3, num_layers=1, num_heads=8, tag_size=4):
        super().__init__()

        self.embedding = nn.Embedding(vocab_num, embed_dim)
        input_size = embed_dim
        if bigram_vocab_num:
            self.bigram_embedding = nn.Embedding(bigram_vocab_num, bigram_embed_dim)
            input_size += num_bigram_per_char*bigram_embed_dim

        self.drop = nn.Dropout(embed_drop_p, inplace=True)

        self.fc1 = nn.Linear(input_size, hidden_size)

        value_size = hidden_size//num_heads
        self.transformer = TransformerEncoder(num_layers, input_size=input_size, output_size=hidden_size,
                                              key_size=value_size, value_size=value_size, num_atte=num_heads)

        self.fc2 = nn.Linear(hidden_size, tag_size)

        allowed_trans = allowed_transitions({0:'b', 1:'m', 2:'e', 3:'s'}, encoding_type='bmes')
        self.crf = ConditionalRandomField(num_tags=tag_size, include_start_end_trans=False,
                                          allowed_transitions=allowed_trans)

    def forward(self, chars, target, seq_lens, bigrams=None):
        seq_lens = seq_lens
        masks = seq_len_to_byte_mask(seq_lens)
        x = self.embedding(chars)
        batch_size = x.size(0)
        length = x.size(1)
        if hasattr(self, 'bigram_embedding'):
            bigrams = self.bigram_embedding(bigrams) # batch_size x seq_lens x per_char x embed_size
            x = torch.cat([x, bigrams.view(batch_size, length, -1)], dim=-1)
        self.drop(x)
        x = self.fc1(x)
        feats = self.transformer(x, masks)
        feats = self.fc2(feats)
        losses = self.crf(feats, target, masks.float())

        pred_dict = {}
        pred_dict['seq_lens'] = seq_lens
        pred_dict['loss'] = torch.mean(losses)

        return pred_dict


if __name__ == '__main__':
    transformer = TransformerCWS(10, embed_dim=100, bigram_vocab_num=10, bigram_embed_dim=100, num_bigram_per_char=8,
                 hidden_size=200, embed_drop_p=0.3, num_layers=1, num_heads=8, tag_size=4)
    chars = torch.randint(10, size=(4, 7)).long()
    bigrams = torch.randint(10, size=(4, 56)).long()
    seq_lens = torch.ones(4).long()*7
    target = torch.randint(4, size=(4, 7))

    print(transformer(chars, target, seq_lens, bigrams))