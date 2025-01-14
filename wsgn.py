import torch
import torch.nn as nn
import torch.nn.functional as F


class WSGN(nn.Module):
    def __init__(self, num_classes=400, spatial_squeeze=True, name='wsgn', dropout_keep_prob=0.8, mode='rgb'):
        super(WSGN, self).__init__()
        self._num_classes = num_classes
        self._spatial_squeeze = spatial_squeeze

        self.logits = nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=1)
        self.dropout = nn.Dropout(dropout_keep_prob)
        self.cls_logits = nn.Conv2d(in_channels=1024, out_channels=self._num_classes, kernel_size=1)
        self.loc_logits = nn.Conv2d(in_channels=1024, out_channels=self._num_classes, kernel_size=1)
        self.s_Cls = nn.Softmax(1)
        self.s_Loc = nn.Softmax(2)
        self.z_Loc = Z_Loc()
        self.g_Loc = G_Loc(num_classes=num_classes)
 

    def forward(self, x):
        x = F.relu(self.logits((self.dropout(x))))
        #x = self.dropout(F.relu(self.logits(x)))
        x = self.dropout(F.relu(x))
        cls_x = self.cls_logits(x)
        loc_x = self.loc_logits(x)
        if self._spatial_squeeze:
            cls_x = cls_x.squeeze(3)
            loc_x = loc_x.squeeze(3)
        cls_x = self.s_Cls(cls_x)
        loc_x = (self.s_Loc(loc_x) + self.z_Loc(loc_x) + self.g_Loc(loc_x)) / 3
        return cls_x, loc_x

class Z_Loc(nn.Module):
    def __init__(self):
        super(Z_Loc, self).__init__()

    def forward(self, x):
        return torch.exp( - (x-x.mean(2).unsqueeze(2).expand_as(x))**2)# / x.var(2,unbiased=False).unsqueeze(2).expand_as(x))


class G_Loc(nn.Module):
    def __init__(self, num_classes=400):
        super(G_Loc, self).__init__()
        self.mean = nn.Parameter(torch.randn(num_classes))
        self.std = nn.Parameter(torch.ones(num_classes))
        
    def forward(self, x):
        return torch.exp( 
            - (x-self.mean.expand(x.size()[0:2]).unsqueeze(2).expand_as(x))**2 
            / self.std.expand(x.size()[0:2]).unsqueeze(2).expand_as(x)**2
        )



class Loc_Sigmoid(nn.Module):
    def __init__(self, dim, alpha, beta):
        super(Loc_Sigmoid, self).__init__()
        self.dim = dim
        self.alpha = alpha
        self.beta = beta

    def forward(self, x):
        means = torch.mean(x, self.dim, keepdim=True)
        x_exp = torch.exp(self.alpha * (self.beta * means - x)) # because multiplied with -1
        return 1 / (1 + x_exp)


class Glob_Sigmoid(nn.Module):
    def __init__(self, dim, alpha, beta, num_classes):
        super(Glob_Sigmoid, self).__init__()
        self.dim = dim
        self.alpha = alpha
        self.beta = beta
        self.mean = nn.Parameter(torch.randn(num_classes))
        
    def forward(self, x):
        x_exp = torch.exp(self.alpha * (self.beta * self.mean.expand(x.size()[0:2]).unsqueeze(2).expand_as(x) - x)) # because multiplied with -1
        return 1 / (1 + x_exp)

class WSSN_Global(nn.Module):
    def __init__(self, num_classes=400, spatial_squeeze=True, name='wsgn', dropout_keep_prob=0.8, mode='rgb'):
        super(WSSN_Global, self).__init__()
        self._num_classes = num_classes
        self._spatial_squeeze = spatial_squeeze

        self.dropout = nn.Dropout(dropout_keep_prob)
        self.cls_logits = nn.Conv2d(in_channels=1024, out_channels=self._num_classes, kernel_size=1)
        self.loc_logits = nn.Conv2d(in_channels=1024, out_channels=self._num_classes, kernel_size=1)
        self.s_Cls = nn.Softmax(1)
        alpha, beta = 2, 1
        print('alpha = {}, beta = {}'.format(alpha, beta))
#        self.sig_Loc = Loc_Sigmoid(dim=2, alpha=alpha, beta=beta)
        self.sig_glob = Glob_Sigmoid(dim=2, alpha=alpha, beta=beta, num_classes=num_classes)
 

    def forward(self, x):
        #x = self.dropout(F.relu(self.logits(F.relu(x))))
        #x = self.dropout(F.relu(self.logits(x)))
        x = self.dropout(F.relu(x))
        cls_x = self.cls_logits(x)
        loc_x = self.loc_logits(x)
        if self._spatial_squeeze:
            cls_x = cls_x.squeeze(3)
            loc_x = loc_x.squeeze(3)
        cls_x = self.s_Cls(cls_x)
        loc_x = self.sig_glob(loc_x)
        return cls_x, loc_x
    
    
class WSSN(nn.Module):
    def __init__(self, num_classes=400, spatial_squeeze=True, name='wsgn', dropout_keep_prob=0.8, mode='rgb'):
        super(WSSN, self).__init__()
        self._num_classes = num_classes
        self._spatial_squeeze = spatial_squeeze

        self.dropout = nn.Dropout(dropout_keep_prob)
        self.cls_logits = nn.Conv2d(in_channels=1024, out_channels=self._num_classes, kernel_size=1)
        self.loc_logits = nn.Conv2d(in_channels=1024, out_channels=self._num_classes, kernel_size=1)
        self.s_Cls = nn.Softmax(1)
        alpha, beta = 1, 1
        print('alpha = {}, beta = {}'.format(alpha, beta))
        self.sig_Loc = Loc_Sigmoid(dim=2, alpha=alpha, beta=beta)
        self.sig_glob = Glob_Sigmoid(dim=2, alpha=alpha, beta=beta, num_classes=num_classes)
 

    def forward(self, x):
        #x = self.dropout(F.relu(self.logits(F.relu(x))))
        #x = self.dropout(F.relu(self.logits(x)))
        x = self.dropout(F.relu(x))
        cls_x = self.cls_logits(x)
        loc_x = self.loc_logits(x)
        if self._spatial_squeeze:
            cls_x = cls_x.squeeze(3)
            loc_x = loc_x.squeeze(3)
        cls_x = self.s_Cls(cls_x)
        loc_x = (self.sig_Loc(loc_x) + self.sig_glob(loc_x)) / 2
        return cls_x, loc_x


class WSGN_sigmoid(nn.Module):
    def __init__(self, num_classes=400, spatial_squeeze=True, name='wsgn', dropout_keep_prob=0.8, mode='rgb'):
        super(WSGN_sigmoid, self).__init__()
        self._num_classes = num_classes
        self._spatial_squeeze = spatial_squeeze

        self.dropout = nn.Dropout(dropout_keep_prob)
        self.cls_logits = nn.Conv2d(in_channels=1024, out_channels=self._num_classes, kernel_size=1)
        self.loc_logits = nn.Conv2d(in_channels=1024, out_channels=self._num_classes, kernel_size=1)
        self.s_Cls = nn.Softmax(1)
        alpha, beta = 2,0.5
        print('alpha = {}, beta = {}'.format(alpha, beta))
        self.sig_Loc = Loc_Sigmoid(dim=2, alpha=alpha, beta=beta)
 

    def forward(self, x):
        #x = self.dropout(F.relu(self.logits(F.relu(x))))
        #x = self.dropout(F.relu(self.logits(x)))
        x = self.dropout(F.relu(x))
        cls_x = self.cls_logits(x)
        loc_x = self.loc_logits(x)
        if self._spatial_squeeze:
            cls_x = cls_x.squeeze(3)
            loc_x = loc_x.squeeze(3)
        cls_x = self.s_Cls(cls_x)
        loc_x = self.sig_Loc(loc_x)
        return cls_x, loc_x
    
    
class WSGN_2fc(nn.Module):
    def __init__(self, num_classes=400, spatial_squeeze=True, name='wsgn', dropout_keep_prob=0.8, mode='rgb'):
        super(WSGN_2fc, self).__init__()
        self._num_classes = num_classes
        self._spatial_squeeze = spatial_squeeze

        
        self.dropout = nn.Dropout(dropout_keep_prob)
        self.cls_logits1 = nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=1)
        self.cls_logits2 = nn.Conv2d(in_channels=1024, out_channels=self._num_classes, kernel_size=1)
        self.loc_logits1 = nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=1)
        self.loc_logits2 = nn.Conv2d(in_channels=1024, out_channels=self._num_classes, kernel_size=1)
        self.s_Cls = nn.Softmax(1)
        self.s_Loc = nn.Softmax(2)
        self.z_Loc = Z_Loc()
        self.g_Loc = G_Loc(num_classes=num_classes)
 

    def forward(self, x):
        #x = self.dropout(F.relu(self.logits(F.relu(x))))
        #x = self.dropout(F.relu(self.logits(x)))
        x = self.dropout(F.relu(x))
        cls_x = F.relu(self.cls_logits1(x))
        cls_x = F.relu(self.cls_logits2(cls_x))
        loc_x = F.relu(self.loc_logits1(x))
        loc_x = F.relu(self.loc_logits2(loc_x))
        if self._spatial_squeeze:
            cls_x = cls_x.squeeze(3)
            loc_x = loc_x.squeeze(3)
        cls_x = self.s_Cls(cls_x)
        loc_x = (self.s_Loc(loc_x) + self.z_Loc(loc_x) + self.g_Loc(loc_x)) / 3
        return cls_x, loc_x