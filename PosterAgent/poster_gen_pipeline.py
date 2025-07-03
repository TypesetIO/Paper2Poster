import argparse
import time

from utils.wei_utils import get_agent_config
from PosterAgent.parse_raw import parse_raw, gen_image_and_table
from PosterAgent.gen_outline_layout import filter_image_table, gen_outline_layout
from PosterAgent.gen_poster_content import gen_poster_content
from PosterAgent.fill_and_style import fill_poster_content, stylize_poster
from PosterAgent.deoverflow import deoverflow
from PosterAgent.apply_theme import poster_apply_theme
from PosterAgent.logger_config import get_logger, log_token_consumption
from PosterAgent.enhanced_token_tracker import save_token_usage_report

logger = get_logger(__name__)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--poster_name', type=str, default=None)
    parser.add_argument('--model_name', type=str, default='4o')
    parser.add_argument('--poster_path', type=str, required=True)
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--template_path', type=str, default=None)
    parser.add_argument('--max_retry', type=int, default=3)
    args = parser.parse_args()

    start_time = time.time()

    actor_config = get_agent_config(args.model_name)
    critic_config = get_agent_config(args.model_name)

    if args.poster_name is None:
        args.poster_name = args.poster_path.split('/')[-1].replace('.pdf', '').replace(' ', '_')

    total_input_token, total_output_token = 0, 0
    
    # Parse raw content
    input_token, output_token = parse_raw(args, actor_config)
    total_input_token += input_token
    total_output_token += output_token

    # Generate images and tables
    _, _ = gen_image_and_table(args)

    log_token_consumption(logger, 'Parsing', input_token, output_token)

    input_token, output_token = filter_image_table(args, actor_config)
    total_input_token += input_token
    total_output_token += output_token
    log_token_consumption(logger, 'Filter images and tables', input_token, output_token)

    input_token, output_token = gen_outline_layout(args, actor_config, critic_config)
    total_input_token += input_token
    total_output_token += output_token
    log_token_consumption(logger, 'Generate outline and layout', input_token, output_token)
    
    input_token, output_token = gen_poster_content(args, actor_config)
    total_input_token += input_token
    total_output_token += output_token
    log_token_consumption(logger, 'Generate poster content', input_token, output_token)

    input_token, output_token = fill_poster_content(args, actor_config)
    total_input_token += input_token
    total_output_token += output_token
    log_token_consumption(logger, 'Fill poster content', input_token, output_token)

    input_token, output_token = stylize_poster(args, actor_config)
    total_input_token += input_token
    total_output_token += output_token
    log_token_consumption(logger, 'Stylize poster', input_token, output_token)

    input_token, output_token = deoverflow(args, actor_config, critic_config)
    total_input_token += input_token
    total_output_token += output_token
    log_token_consumption(logger, 'Deoverflow', input_token, output_token)

    if args.template_path is not None:
        input_token, output_token = poster_apply_theme(args, actor_config, critic_config)
        total_input_token += input_token
        total_output_token += output_token
        log_token_consumption(logger, 'Apply theme', input_token, output_token)

    log_token_consumption(logger, 'Total', total_input_token, total_output_token)

    end_time = time.time()
    elapsed_time = end_time - start_time
    # Convert to hh:mm:ss format
    hours, rem = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(rem, 60)

    logger.info(f"Execution Time: {int(hours):02}:{int(minutes):02}:{int(seconds):02}")

    log_path = f'log/{args.model_name}_{args.poster_name}_{args.index}_log.txt'
    with open(log_path, 'w') as f:
        f.write(f'Total token consumption: {total_input_token} -> {total_output_token}\n')
        f.write(f'Execution Time: {int(hours):02}:{int(minutes):02}:{int(seconds):02}\n')
    
    # Save detailed token usage report with costs
    detailed_report_path = f'log/{args.model_name}_{args.poster_name}_{args.index}_token_report.json'
    save_token_usage_report(detailed_report_path)
        