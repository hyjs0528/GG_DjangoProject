from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.views.generic import ListView, DetailView
from .models import h_Chat, h_Comment
from .forms import *
from bcuser.models import Bcuser
from django.core.paginator import Paginator
from django.db import models
# Create your views here.

# def chat_list(request):
#     all_chats = h_Chat.objects.all().order_by("-id")
#     page = int(request.GET.get('p', 1))  # 초기에 페이지는 1로 시작
#     paginator = Paginator(all_chats, 10)  # 전체 글을 가져와서 10개씩 나누어 보여줌


#     chats = paginator.get_page(page)


#     return render(request, 'h_chat_list.html', {'chats': chats})
def chat_list(request):
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search_query')

    all_chats = h_Chat.objects.all().order_by("-h_register_date")
    
    if category_filter and category_filter != '전체':
        all_chats = all_chats.filter(h_category=category_filter)

    if search_query:
        all_chats = all_chats.filter(h_title__icontains=search_query)
    
    page = int(request.GET.get('p', 1))
    paginator = Paginator(all_chats, 10)
    chats = paginator.get_page(page)

    form = ChatSearchForm(request.GET)
    
    context = {
        'chats': chats,
        'form': form,
    }

    return render(request, 'h_chat_list.html', context)

def board_write(request):
    # 세션영역에 id가 존재하지 않으면 로그인 하고 오도록 login.html페이지로 넘김(ok)
    if not request.session.get('user'):
        return redirect('/login/')

    if request.method == 'POST':
        form = h_ChatForm(request.POST)
        print(request.POST) 
        if form.is_valid():  # 폼이 유효한지(ok 빈값일때 에러메시지 확인)
            #user_id = request.session.get('user')  # 세션에서 로그인한 아이디 확보
            # 실제 데이터 베이스에서 로그인한 id 가져오기
            #bcuser = form.data.get('email')

            chat = h_Chat()  # 게시판의 객체 생성 : 유효성 검사가 통과된 데이터를 저장하기 위함
            chat.h_category = form.cleaned_data['category']
            chat.h_title = form.cleaned_data['title']
            chat.h_contents = form.cleaned_data['contents']
            chat.h_writer = Bcuser.objects.get(email=request.session.get('user')) # 로그인한 id 데이터베이스에 저장
            chat.save()

            return redirect('/chat_board/')
    else:
        form = h_ChatForm()  # 접속은 했으나 유효성 검사를 안했으므로 다시 유효성 검사부터 진행
    # 실패시 처음으로 돌아가서 다시해봐
    return render(request, 'h_chat_write.html', {'form': form})


def board_delete(request, pk):
    chat = get_object_or_404(h_Chat, pk=pk)

    # 로그인한 사용자와 채팅 메시지 작성자가 같은지 확인
    if Bcuser.objects.get(email=request.session.get('user')) == chat.h_writer:
        chat.delete()
        return redirect('/chat_board/')  # 채팅 목록 페이지로 리다이렉트
    else:
        raise Http404('권한이 없습니다')
    
#######################
def comment_delete(request,pk):
    comment = get_object_or_404(h_Comment, pk=pk)
    if comment.author == Bcuser.objects.get(email=request.session.get('user')):
        chat_pk = comment.post.pk  # 코멘트가 속한 게시글의 pk 가져오기
        comment.delete()
        return redirect('chat_board_detail', pk=chat_pk)  # 게시글 상세 페이지로 리다이렉트
    else:
        raise Http404('권한이 없습니다')
    
def board_vote(request, pk):
    chat = h_Chat.objects.get(pk=pk)
    user = Bcuser.objects.get(email=request.session.get('user')) # 현재 로그인한 사용자
    
        # 중복 추천 확인
    if user in chat.h_voters.all():
        chat.h_votes -= 1  # 추천수 감소
        chat.h_voters.remove(user)  # 사용자를 추천한 사용자 목록에서 제거
        is_upvoted = False # 추천 취소됨
    else:
        chat.h_votes += 1  # 추천수 증가
        chat.h_voters.add(user)  # 해당 사용자를 추천한 사용자 목록에 추가
        is_upvoted = True  # 추천됨
        
    chat.save()
    return redirect('chat_board_detail', pk=chat.pk)

def board_detail(request, pk):
    try:
        chat = h_Chat.objects.get(pk=pk)
    except h_Chat.DoesNotExist:
        raise Http404('게시글을 찾을 수 없습니다.')
    
    chat.h_click += 1
    chat.save()
    
        # 중복 추천 확인
    user = Bcuser.objects.get(email=request.session.get('user'))
    is_upvoted = user in chat.h_voters.all()
    
    
    ########################댓글 구성 구분########################################
    comments = h_Comment.objects.filter(post=chat)
    
    
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = chat
            new_comment.author = Bcuser.objects.get(email=request.session.get('user'))
            new_comment.save()
            return redirect('chat_board_detail', pk=chat.pk)
    else:
        comment_form = CommentForm()

    context = {
    'chat': chat,
    'comment_form': comment_form,
    'comments': comments,
    'is_upvoted': is_upvoted,  
    }
    return render(request, 'h_chat_detail.html', context)



def board_update(request, pk):
    if not request.session.get('user'):
        return redirect('/login/')

    try:
        chat = h_Chat.objects.get(pk=pk)
    except h_Chat.DoesNotExist:  # 게시글이 없을때 다음 메시지를 띄움
        raise Http404('게시글을 찾을 수 없습니다.')

    if request.method == 'POST':
        form = h_ChatForm(request.POST)
        if form.is_valid():  # 폼이 유효한지
            user_id = request.session.get('user') # 세션에서 로그인한 아이디 확보
            chat.h_category = form.cleaned_data['category']
            chat.h_title = form.cleaned_data['title']
            chat.h_contents = form.cleaned_data['contents']
            chat.h_writer = Bcuser.objects.get(email=request.session.get('user'))
            chat.save()
            return redirect('/chat_board/')
    else:
        form = h_ChatForm(initial={'title':chat.h_title, 'contents':chat.h_contents, 'category':chat.h_category})
    return render(request, 'h_chat_update.html', {'form': form})

